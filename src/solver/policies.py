import random
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass
class PolicyContext:
    rem_weights: Sequence[float]
    ins_weights: Sequence[float]
    noise_weights: Sequence[float]
    iteration: int
    stage: str


class BaseSelectionPolicy:
    """Base interface for operator/noise selection policies."""

    def begin_run(self) -> None:
        return

    def select(
        self,
        state_vector: Sequence[float],
        num_removal_ops: int,
        num_insertion_ops: int,
        context: PolicyContext,
    ) -> Tuple[int, int, int]:
        raise NotImplementedError("Selection policy must implement select().")

    def observe(
        self,
        state_vector: Sequence[float],
        reward: float,
        accepted: bool,
        is_new_best: bool,
    ) -> None:
        return


class RouletteSelectionPolicy(BaseSelectionPolicy):
    """Keeps original roulette behavior as the default baseline."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng if rng is not None else random

    def select(
        self,
        state_vector: Sequence[float],
        num_removal_ops: int,
        num_insertion_ops: int,
        context: PolicyContext,
    ) -> Tuple[int, int, int]:
        rem_idx = self.rng.choices(range(num_removal_ops), weights=context.rem_weights, k=1)[0]
        ins_idx = self.rng.choices(range(num_insertion_ops), weights=context.ins_weights, k=1)[0]
        noise_idx = self.rng.choices([0, 1], weights=context.noise_weights, k=1)[0]
        return rem_idx, ins_idx, noise_idx


class OnlineLinearBanditPolicy(BaseSelectionPolicy):
    """Contextual bandit policy using LinUCB over removal and noise actions."""

    def __init__(
        self,
        feature_dim: int,
        alpha: float = 0.8,
        epsilon: float = 0.05,
        rng: Optional[random.Random] = None,
    ):
        self.feature_dim = max(1, int(feature_dim))
        self.alpha = alpha
        self.epsilon = epsilon
        self.rng = rng if rng is not None else random

        self._rem_A: List[List[float]] = []
        self._rem_b: List[List[float]] = []
        self._noise_A: List[List[float]] = []
        self._noise_b: List[List[float]] = []

        self._last_rem_idx: Optional[int] = None
        self._last_noise_idx: Optional[int] = None
        self._last_x: Optional[List[float]] = None

    def begin_run(self) -> None:
        self._last_rem_idx = None
        self._last_noise_idx = None
        self._last_x = None

    def _init_arms(self, num_arms: int) -> Tuple[List[List[float]], List[List[float]]]:
        A = []
        b = []
        for _ in range(num_arms):
            ident = [0.0] * (self.feature_dim * self.feature_dim)
            for i in range(self.feature_dim):
                ident[i * self.feature_dim + i] = 1.0
            A.append(ident)
            b.append([0.0] * self.feature_dim)
        return A, b

    def _mat_vec(self, A: List[float], x: Sequence[float]) -> List[float]:
        out = [0.0] * self.feature_dim
        for i in range(self.feature_dim):
            row_base = i * self.feature_dim
            acc = 0.0
            for j in range(self.feature_dim):
                acc += A[row_base + j] * x[j]
            out[i] = acc
        return out

    def _dot(self, a: Sequence[float], b: Sequence[float]) -> float:
        return sum(ai * bi for ai, bi in zip(a, b))

    def _solve(self, A: List[float], b: Sequence[float]) -> List[float]:
        # Small dense solve using Gaussian elimination on copied matrix.
        n = self.feature_dim
        M = [A[i * n:(i + 1) * n] for i in range(n)]
        y = list(b)

        for col in range(n):
            pivot = col
            for row in range(col + 1, n):
                if abs(M[row][col]) > abs(M[pivot][col]):
                    pivot = row
            if abs(M[pivot][col]) < 1e-12:
                continue
            if pivot != col:
                M[col], M[pivot] = M[pivot], M[col]
                y[col], y[pivot] = y[pivot], y[col]

            pv = M[col][col]
            inv_pv = 1.0 / pv
            for j in range(col, n):
                M[col][j] *= inv_pv
            y[col] *= inv_pv

            for row in range(n):
                if row == col:
                    continue
                factor = M[row][col]
                if abs(factor) < 1e-12:
                    continue
                for j in range(col, n):
                    M[row][j] -= factor * M[col][j]
                y[row] -= factor * y[col]

        return y

    def _linucb_score(self, A: List[float], b: List[float], x: Sequence[float]) -> float:
        theta = self._solve(A, b)
        pred = self._dot(theta, x)

        invA_x = self._solve(A, x)
        x_invA_x = max(0.0, self._dot(x, invA_x))
        bonus = self.alpha * (x_invA_x ** 0.5)
        return pred + bonus

    def _select_arm(self, A_list: List[List[float]], b_list: List[List[float]], x: Sequence[float]) -> int:
        if self.rng.random() < self.epsilon:
            return self.rng.randrange(len(A_list))

        best_idx = 0
        best_score = float("-inf")
        for idx in range(len(A_list)):
            score = self._linucb_score(A_list[idx], b_list[idx], x)
            if score > best_score:
                best_score = score
                best_idx = idx
        return best_idx

    def _ensure_models(self, num_removal_ops: int) -> None:
        if not self._rem_A or len(self._rem_A) != num_removal_ops:
            self._rem_A, self._rem_b = self._init_arms(num_removal_ops)
        if not self._noise_A or len(self._noise_A) != 2:
            self._noise_A, self._noise_b = self._init_arms(2)

    def select(
        self,
        state_vector: Sequence[float],
        num_removal_ops: int,
        num_insertion_ops: int,
        context: PolicyContext,
    ) -> Tuple[int, int, int]:
        x = list(state_vector)
        if len(x) < self.feature_dim:
            x.extend([0.0] * (self.feature_dim - len(x)))
        elif len(x) > self.feature_dim:
            x = x[:self.feature_dim]

        self._ensure_models(num_removal_ops)

        rem_idx = self._select_arm(self._rem_A, self._rem_b, x)

        # Current codebase has one insertion operator; keep deterministic.
        ins_idx = 0 if num_insertion_ops > 0 else -1

        noise_idx = self._select_arm(self._noise_A, self._noise_b, x)

        self._last_rem_idx = rem_idx
        self._last_noise_idx = noise_idx
        self._last_x = x
        return rem_idx, ins_idx, noise_idx

    def _rank1_update(self, A: List[float], b: List[float], x: Sequence[float], reward: float) -> None:
        n = self.feature_dim
        for i in range(n):
            b[i] += reward * x[i]
            row_base = i * n
            xi = x[i]
            for j in range(n):
                A[row_base + j] += xi * x[j]

    def observe(
        self,
        state_vector: Sequence[float],
        reward: float,
        accepted: bool,
        is_new_best: bool,
    ) -> None:
        if self._last_x is None:
            return
        shaped_reward = reward
        if not accepted:
            shaped_reward -= 0.02
        if is_new_best:
            shaped_reward += 0.05

        if self._last_rem_idx is not None:
            self._rank1_update(
                self._rem_A[self._last_rem_idx],
                self._rem_b[self._last_rem_idx],
                self._last_x,
                shaped_reward,
            )
        if self._last_noise_idx is not None:
            self._rank1_update(
                self._noise_A[self._last_noise_idx],
                self._noise_b[self._last_noise_idx],
                self._last_x,
                shaped_reward,
            )
