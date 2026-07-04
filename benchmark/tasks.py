"""Benchmark task suite — Python coding tasks with automatic validators.

Tasks are HumanEval-style (small functions). Each task has:
- a clear natural-language prompt;
- a function name the answer must define;
- a hidden test harness that runs once the agent submits.

The split (wake_split / heldout_split) is fixed by `seed` so the experiment
is reproducible: skills learned on wake_split are tested on heldout_split.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from engram.config import CONFIG
from engram.tools import PythonExecutor


@dataclass
class BenchmarkTask:
    id: str
    prompt: str
    function_name: str
    test_code: str  # asserts that exit non-zero on failure, prints "PASS" on success
    family: str = "general"
    difficulty: int = 1  # 1=easy, 2=med, 3=hard

    def validator_for(self, executor: PythonExecutor):
        """Build a Validator closure (signature: (answer:str) -> (ok:bool, msg:str))."""
        def _validate(answer: str) -> tuple[bool, str]:
            answer = _strip_code_fences(answer)
            full = answer.rstrip() + "\n\n# ---- VALIDATOR ----\n" + self.test_code
            res = executor.run(full)
            if not res.ok:
                msg = (res.error or res.output)[:300]
                return False, f"runtime_error: {msg}"
            if "PASS" in res.output:
                return True, "tests passed"
            return False, f"tests failed: stdout={res.output[:200]}"
        return _validate


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        # remove first and last ``` lines
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines)
    return text


# ----- Task definitions ----------------------------------------------------

TASKS: list[BenchmarkTask] = [
    # ---- Number-theory family ----
    BenchmarkTask(
        id="num_001_fib",
        family="num_theory",
        difficulty=1,
        prompt=(
            "Define a Python function `fib(n)` that returns the n-th Fibonacci number "
            "(fib(0)=0, fib(1)=1). Must handle n up to 30 efficiently."
        ),
        function_name="fib",
        test_code=(
            "assert fib(0) == 0\n"
            "assert fib(1) == 1\n"
            "assert fib(10) == 55\n"
            "assert fib(20) == 6765\n"
            "assert fib(30) == 832040\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="num_002_isprime",
        family="num_theory",
        difficulty=1,
        prompt="Define `is_prime(n: int) -> bool`. Returns True iff n is prime.",
        function_name="is_prime",
        test_code=(
            "for n in [2,3,5,7,11,13,17,19,23,29]: assert is_prime(n), n\n"
            "for n in [0,1,4,6,8,9,10,15,21,25]: assert not is_prime(n), n\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="num_003_gcd",
        family="num_theory",
        difficulty=1,
        prompt="Define `gcd(a: int, b: int) -> int` (Euclidean algorithm).",
        function_name="gcd",
        test_code=(
            "assert gcd(12, 18) == 6\n"
            "assert gcd(100, 75) == 25\n"
            "assert gcd(7, 13) == 1\n"
            "assert gcd(0, 5) == 5\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="num_004_factorial",
        family="num_theory",
        difficulty=1,
        prompt="Define `factorial(n: int) -> int`. n>=0.",
        function_name="factorial",
        test_code=(
            "assert factorial(0) == 1\n"
            "assert factorial(1) == 1\n"
            "assert factorial(5) == 120\n"
            "assert factorial(10) == 3628800\n"
            "print('PASS')\n"
        ),
    ),

    # ---- String family ----
    BenchmarkTask(
        id="str_001_palindrome",
        family="strings",
        difficulty=1,
        prompt="Define `is_palindrome(s: str) -> bool` ignoring case and non-alphanumerics.",
        function_name="is_palindrome",
        test_code=(
            "assert is_palindrome('A man, a plan, a canal: Panama')\n"
            "assert is_palindrome('racecar')\n"
            "assert is_palindrome('') == True\n"
            "assert not is_palindrome('hello')\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="str_002_reverse_words",
        family="strings",
        difficulty=1,
        prompt="Define `reverse_words(s: str) -> str` reversing the order of whitespace-separated words.",
        function_name="reverse_words",
        test_code=(
            "assert reverse_words('hello world') == 'world hello'\n"
            "assert reverse_words('a b c') == 'c b a'\n"
            "assert reverse_words('one') == 'one'\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="str_003_count_vowels",
        family="strings",
        difficulty=1,
        prompt="Define `count_vowels(s: str) -> int` counting a/e/i/o/u (case-insensitive).",
        function_name="count_vowels",
        test_code=(
            "assert count_vowels('hello') == 2\n"
            "assert count_vowels('AEIOU') == 5\n"
            "assert count_vowels('') == 0\n"
            "assert count_vowels('xyz') == 0\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="str_004_anagram",
        family="strings",
        difficulty=2,
        prompt=(
            "Define `is_anagram(a: str, b: str) -> bool` — True if a and b are anagrams "
            "ignoring whitespace and case."
        ),
        function_name="is_anagram",
        test_code=(
            "assert is_anagram('listen', 'silent')\n"
            "assert is_anagram('Triangle', 'Integral')\n"
            "assert is_anagram('a b c', 'cab')\n"
            "assert not is_anagram('hello', 'world')\n"
            "print('PASS')\n"
        ),
    ),

    # ---- List family ----
    BenchmarkTask(
        id="lst_001_max_subarray",
        family="lists",
        difficulty=2,
        prompt=(
            "Define `max_subarray_sum(arr: list[int]) -> int` — maximum sum of any "
            "contiguous non-empty subarray (Kadane's algorithm)."
        ),
        function_name="max_subarray_sum",
        test_code=(
            "assert max_subarray_sum([-2,1,-3,4,-1,2,1,-5,4]) == 6\n"
            "assert max_subarray_sum([1]) == 1\n"
            "assert max_subarray_sum([-1,-2,-3]) == -1\n"
            "assert max_subarray_sum([5,4,-1,7,8]) == 23\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="lst_002_unique_in_order",
        family="lists",
        difficulty=1,
        prompt=(
            "Define `unique_in_order(seq: list) -> list` — keep only elements that "
            "differ from their predecessor. e.g. [1,1,2,2,3,1] -> [1,2,3,1]."
        ),
        function_name="unique_in_order",
        test_code=(
            "assert unique_in_order([1,1,2,2,3,1]) == [1,2,3,1]\n"
            "assert unique_in_order([]) == []\n"
            "assert unique_in_order(['a','a','b','c','c']) == ['a','b','c']\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="lst_003_chunk",
        family="lists",
        difficulty=1,
        prompt="Define `chunk(arr: list, k: int) -> list[list]` splitting arr into chunks of size k.",
        function_name="chunk",
        test_code=(
            "assert chunk([1,2,3,4,5], 2) == [[1,2],[3,4],[5]]\n"
            "assert chunk([], 3) == []\n"
            "assert chunk([1,2,3], 5) == [[1,2,3]]\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="lst_004_two_sum",
        family="lists",
        difficulty=2,
        prompt=(
            "Define `two_sum(nums: list[int], target: int) -> tuple[int,int] | None` — "
            "return indices (i,j) i<j of two distinct elements summing to target, "
            "or None if none. Prefer O(n)."
        ),
        function_name="two_sum",
        test_code=(
            "assert two_sum([2,7,11,15], 9) == (0,1)\n"
            "assert two_sum([3,2,4], 6) == (1,2)\n"
            "assert two_sum([1,2,3], 100) is None\n"
            "print('PASS')\n"
        ),
    ),

    # ---- Algorithmic ----
    BenchmarkTask(
        id="alg_001_binsearch",
        family="algorithms",
        difficulty=2,
        prompt=(
            "Define `binary_search(arr: list[int], target: int) -> int` — index of "
            "target in sorted arr, or -1 if absent. Must be O(log n)."
        ),
        function_name="binary_search",
        test_code=(
            "assert binary_search([1,3,5,7,9,11], 7) == 3\n"
            "assert binary_search([1,3,5,7,9,11], 1) == 0\n"
            "assert binary_search([1,3,5,7,9,11], 11) == 5\n"
            "assert binary_search([1,3,5,7,9,11], 4) == -1\n"
            "assert binary_search([], 5) == -1\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="alg_002_pow_int",
        family="algorithms",
        difficulty=2,
        prompt=(
            "Define `power(x: float, n: int) -> float` — x to the n. Handle negative n. "
            "Prefer O(log n) via fast exponentiation. No use of ** or pow()."
        ),
        function_name="power",
        test_code=(
            "assert abs(power(2, 10) - 1024) < 1e-9\n"
            "assert abs(power(2, -3) - 0.125) < 1e-9\n"
            "assert abs(power(3, 0) - 1) < 1e-9\n"
            "assert abs(power(5, 5) - 3125) < 1e-9\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="alg_003_balanced_parens",
        family="algorithms",
        difficulty=2,
        prompt=(
            "Define `is_balanced(s: str) -> bool` — True iff parens/brackets/braces "
            "in s are properly matched and nested."
        ),
        function_name="is_balanced",
        test_code=(
            "assert is_balanced('()[]{}')\n"
            "assert is_balanced('([{}])')\n"
            "assert not is_balanced('([)]')\n"
            "assert not is_balanced('(')\n"
            "assert is_balanced('')\n"
            "print('PASS')\n"
        ),
    ),

    # ---- Higher-difficulty / held-out skewed ----
    BenchmarkTask(
        id="alg_004_lis",
        family="algorithms",
        difficulty=3,
        prompt=(
            "Define `length_of_lis(nums: list[int]) -> int` — length of the longest "
            "strictly increasing subsequence. Aim for O(n log n)."
        ),
        function_name="length_of_lis",
        test_code=(
            "assert length_of_lis([10,9,2,5,3,7,101,18]) == 4\n"
            "assert length_of_lis([0,1,0,3,2,3]) == 4\n"
            "assert length_of_lis([7,7,7,7]) == 1\n"
            "assert length_of_lis([]) == 0\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="num_005_digit_sum",
        family="num_theory",
        difficulty=1,
        prompt="Define `digit_sum(n: int) -> int` — sum of base-10 digits of |n|.",
        function_name="digit_sum",
        test_code=(
            "assert digit_sum(0) == 0\n"
            "assert digit_sum(123) == 6\n"
            "assert digit_sum(-987) == 24\n"
            "print('PASS')\n"
        ),
    ),
    BenchmarkTask(
        id="lst_005_flatten",
        family="lists",
        difficulty=2,
        prompt=(
            "Define `flatten(nested: list) -> list` — recursively flatten arbitrarily "
            "nested lists into a single flat list."
        ),
        function_name="flatten",
        test_code=(
            "assert flatten([1,[2,[3,4],5]]) == [1,2,3,4,5]\n"
            "assert flatten([]) == []\n"
            "assert flatten([[1],[2,[3]]]) == [1,2,3]\n"
            "print('PASS')\n"
        ),
    ),
]


def get_task(task_id: str) -> BenchmarkTask:
    for t in TASKS:
        if t.id == task_id:
            return t
    raise KeyError(task_id)


def wake_split(seed: int | None = None, ratio: float = 0.6) -> list[BenchmarkTask]:
    """Deterministic train/wake portion."""
    rng = random.Random(seed if seed is not None else CONFIG.seed)
    shuffled = list(TASKS)
    rng.shuffle(shuffled)
    n = int(len(shuffled) * ratio)
    return shuffled[:n]


def heldout_split(seed: int | None = None, ratio: float = 0.6) -> list[BenchmarkTask]:
    """Deterministic held-out portion (complement of wake_split)."""
    rng = random.Random(seed if seed is not None else CONFIG.seed)
    shuffled = list(TASKS)
    rng.shuffle(shuffled)
    n = int(len(shuffled) * ratio)
    return shuffled[n:]
