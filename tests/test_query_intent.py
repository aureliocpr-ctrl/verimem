"""Query intent router — read-path twin of gate_router (surface map thesis).

The engine classifies before it acts: provenance on write, INTENT on read.
FIND is the safe default (unchanged recall), so a query only re-routes on a
clear cardinality / enumeration / exclusion signal. EN + IT (Aurelio).
"""
from __future__ import annotations

import pytest

from engram.query_intent import (
    COUNT,
    EXCLUDE,
    FIND,
    LIST_ALL,
    classify_query_intent,
    is_set_operation,
)


@pytest.mark.parametrize("q", [
    "how many times did I mention Project Helios?",
    "how many meetings this week",
    "number of open tickets",
    "how often did we discuss the budget",
    "quante volte ho parlato di Helios?",
    "quanti progetti sono attivi",
    "numero di riunioni",
])
def test_count_queries(q):
    assert classify_query_intent(q) == COUNT


@pytest.mark.parametrize("q", [
    "list all the meetings about Helios",
    "show me all open tickets",
    "elenca tutti i progetti",
    "mostrami tutte le riunioni",
])
def test_list_all_queries(q):
    assert classify_query_intent(q) == LIST_ALL


@pytest.mark.parametrize("q", [
    "notes not about tax",
    "everything except the Helios project",
    "tickets excluding closed ones",
    "note che non riguardano le tasse",
    "progetti tranne Helios",
])
def test_exclude_queries(q):
    assert classify_query_intent(q) == EXCLUDE


@pytest.mark.parametrize("q", [
    "where is the Eiffel Tower?",
    "what is the Q3 marketing budget",
    "who is the CEO of Kappa Dynamics",
    "dove si trova la torre Eiffel",
    "",
    "   ",
])
def test_find_is_the_safe_default(q):
    assert classify_query_intent(q) == FIND


def test_is_set_operation_bit():
    assert is_set_operation("how many times X") is True
    assert is_set_operation("list all X") is True
    assert is_set_operation("notes not about X") is True
    assert is_set_operation("where is X") is False
    assert is_set_operation("") is False


def test_count_wins_over_list_all():
    # "how many of all the…" is a count, not an enumeration
    assert classify_query_intent("how many of all the tickets are open") == COUNT
