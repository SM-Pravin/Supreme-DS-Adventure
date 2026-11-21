#!/usr/bin/env python3
"""
Interactive Step-by-Step van Emde Boas (vEB) Tree Visualizer
============================================================
An interactive Tkinter GUI for visualizing every single instruction of a
van Emde Boas (vEB) Tree (insert, deleteVal, member, successor, predecessor),
faithfully matching the C implementation in `vanEmdeBoasTrees.h`.

Usage:
    python veb_visualizer.py

Requirements:
    Python 3.8+ standard library only (tkinter). No external packages needed.
"""

from dataclasses import dataclass, field
import random
import re
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Helpers (matching vanEmdeBoasTrees.h)
# ---------------------------------------------------------------------------

def upper_sqrt(u: int) -> int:
    """2^ceil(log2(u) / 2) using exact integer arithmetic."""
    k = u.bit_length() - 1
    return 1 << ((k + 1) // 2)


def lower_sqrt(u: int) -> int:
    """2^floor(log2(u) / 2) using exact integer arithmetic."""
    k = u.bit_length() - 1
    return 1 << (k // 2)


def fmt_val(v: Optional[int]) -> str:
    return "NIL" if v is None else str(v)


# ---------------------------------------------------------------------------
# Code listings displayed in the Live Code Execution Panel
# (1-based line numbers matching vanEmdeBoasTrees.h)
# ---------------------------------------------------------------------------

CODE_LISTINGS: Dict[str, List[str]] = {
    "insert": [
        "void insert(vEB* tree, int x) {",
        "  if (tree->min == NIL) {",
        "    emptyInsert(tree, x); // min = max = x",
        "    return;",
        "  }",
        "  if (x < tree->min) {",
        "    swap(x, tree->min); // keep smaller in min",
        "  }",
        "  if (tree->universeSize > 2) {",
        "    h = high(tree, x); l = low(tree, x);",
        "    if (tree->clusters[h]->min == NIL) {",
        "      insert(tree->summary, h);",
        "      emptyInsert(tree->clusters[h], l);",
        "    } else {",
        "      insert(tree->clusters[h], l);",
        "    }",
        "  }",
        "  if (x > tree->max) {",
        "    tree->max = x;",
        "  }",
        "}",
    ],
    "member": [
        "int member(vEB* tree, int x) {",
        "  if (x == tree->min || x == tree->max) {",
        "    return 1; // Found!",
        "  }",
        "  if (tree->universeSize <= 2) {",
        "    return 0; // Base case: not found",
        "  }",
        "  h = high(tree, x); l = low(tree, x);",
        "  return member(tree->clusters[h], l);",
        "}",
    ],
    "successor": [
        "int successor(vEB* tree, int x) {",
        "  if (tree->universeSize <= 2) {",
        "    if (x == 0 && tree->max == 1) return 1;",
        "    return NIL;",
        "  }",
        "  if (tree->min != NIL && x < tree->min) {",
        "    return tree->min;",
        "  }",
        "  h = high(tree, x); l = low(tree, x);",
        "  maxLow = tree->clusters[h]->max;",
        "  if (maxLow != NIL && l < maxLow) {",
        "    offset = successor(tree->clusters[h], l);",
        "    return indexOf(tree, h, offset);",
        "  } else {",
        "    succCluster = successor(tree->summary, h);",
        "    if (succCluster == NIL) return NIL;",
        "    offset = tree->clusters[succCluster]->min;",
        "    return indexOf(tree, succCluster, offset);",
        "  }",
        "}",
    ],
    "predecessor": [
        "int predecessor(vEB* tree, int x) {",
        "  if (tree->universeSize <= 2) {",
        "    if (x == 1 && tree->min == 0) return 0;",
        "    return NIL;",
        "  }",
        "  if (tree->max != NIL && x > tree->max) {",
        "    return tree->max;",
        "  }",
        "  h = high(tree, x); l = low(tree, x);",
        "  minLow = tree->clusters[h]->min;",
        "  if (minLow != NIL && l > minLow) {",
        "    offset = predecessor(tree->clusters[h], l);",
        "    return indexOf(tree, h, offset);",
        "  } else {",
        "    predCluster = predecessor(tree->summary, h);",
        "    if (predCluster == NIL) {",
        "      if (tree->min != NIL && x > tree->min) return tree->min;",
        "      return NIL;",
        "    }",
        "    offset = tree->clusters[predCluster]->max;",
        "    return indexOf(tree, predCluster, offset);",
        "  }",
        "}",
    ],
    "deleteVal": [
        "void deleteVal(vEB* tree, int x) {",
        "  if (tree->min == tree->max) {",
        "    tree->min = NIL; tree->max = NIL; return;",
        "  }",
        "  if (tree->universeSize <= 2) {",
        "    tree->min = (x == 0) ? 1 : 0;",
        "    tree->max = tree->min; return;",
        "  }",
        "  if (x == tree->min) {",
        "    firstCluster = tree->summary->min;",
        "    x = indexOf(tree, firstCluster, clusters[firstCluster]->min);",
        "    tree->min = x;",
        "  }",
        "  h = high(tree, x); l = low(tree, x);",
        "  deleteVal(tree->clusters[h], l);",
        "  if (tree->clusters[h]->min == NIL) {",
        "    deleteVal(tree->summary, h);",
        "    if (x == tree->max) {",
        "      summaryMax = tree->summary->max;",
        "      if (summaryMax == NIL) tree->max = tree->min;",
        "      else tree->max = indexOf(tree, summaryMax, clusters[summaryMax]->max);",
        "    }",
        "  } else if (x == tree->max) {",
        "    tree->max = indexOf(tree, h, tree->clusters[h]->max);",
        "  }",
        "}",
    ],
}


# ---------------------------------------------------------------------------
# Step Snapshot Data Model
# ---------------------------------------------------------------------------

@dataclass
class StepSnapshot:
    step_index: int
    op_label: str                                      # e.g. "insert(7)"
    op_name: str                                       # e.g. "insert"
    active_line: int                                   # 1-based line in CODE_LISTINGS[op_name]
    active_node_id: str                                # Node ID currently executing
    node_states: Dict[str, Tuple[Optional[int], Optional[int]]]  # node_id -> (min, max)
    node_roles: Dict[str, str]                         # node_id -> visual highlight role
    field_highlights: Dict[str, Set[str]]              # node_id -> {"min", "max"}
    active_edge: Optional[Tuple[str, str]]             # (parent_id, child_id)
    stack_edges: List[Tuple[str, str]]                 # edges along current recursion path
    call_stack: List[str]                              # readable stack frames
    variables: Dict[str, str]                          # local vars at this step
    node_badge: str                                    # short badge above active node
    explanation: str                                   # plain-English narration
    elements: Set[int]                                 # current elements in root tree
    query_x: Optional[int] = None                      # top-level x argument
    in_flight_x: Optional[int] = None                  # value currently carried (e.g. after swap)
    result_val: Optional[str] = None                   # final / intermediate return value


# ---------------------------------------------------------------------------
# Instrumented van Emde Boas Tree Engine
# ---------------------------------------------------------------------------

class VEBNode:
    """Single node of a van Emde Boas tree with metadata for visualization."""

    def __init__(
        self,
        u: int,
        node_id: str,
        label: str,
        is_summary: bool = False,
        parent_id: Optional[str] = None,
        range_label: str = "",
    ):
        self.u: int = u
        self.node_id: str = node_id
        self.label: str = label
        self.is_summary: bool = is_summary
        self.parent_id: Optional[str] = parent_id
        self.range_label: str = range_label
        self.min: Optional[int] = None
        self.max: Optional[int] = None
        self.summary: Optional["VEBNode"] = None
        self.clusters: List["VEBNode"] = []

        if u > 2:
            upper = upper_sqrt(u)
            lower = lower_sqrt(u)
            self.summary = VEBNode(
                u=upper,
                node_id=f"{node_id}.S",
                label="SUM",
                is_summary=True,
                parent_id=node_id,
                range_label=f"idx 0..{upper - 1}",
            )
            for i in range(upper):
                if is_summary:
                    c_range = f"idx {i * lower}..{(i + 1) * lower - 1}"
                else:
                    # Parse global start if parent has numeric range
                    if ".." in range_label and not range_label.startswith("idx"):
                        base = int(range_label.split("..")[0])
                        lo = base + i * lower
                        hi = lo + lower - 1
                        c_range = f"{lo}..{hi}"
                    else:
                        c_range = f"{i * lower}..{(i + 1) * lower - 1}"
                self.clusters.append(
                    VEBNode(
                        u=lower,
                        node_id=f"{node_id}.C{i}",
                        label=f"C[{i}]",
                        is_summary=is_summary,
                        parent_id=node_id,
                        range_label=c_range,
                    )
                )

    def high(self, x: int) -> int:
        return x // lower_sqrt(self.u)

    def low(self, x: int) -> int:
        return x % lower_sqrt(self.u)

    def index_of(self, h: int, l: int) -> int:
        return h * lower_sqrt(self.u) + l

    def all_nodes(self) -> List["VEBNode"]:
        result = [self]
        if self.summary is not None:
            result.extend(self.summary.all_nodes())
        for c in self.clusters:
            result.extend(c.all_nodes())
        return result


class VEBEngine:
    """Manages a vEB tree and records instruction-by-instruction StepSnapshots."""

    def __init__(self, u: int = 16):
        self.u: int = u
        self.root: VEBNode = VEBNode(
            u=u,
            node_id="root",
            label="ROOT",
            is_summary=False,
            parent_id=None,
            range_label=f"0..{u - 1}",
        )
        self.node_map: Dict[str, VEBNode] = {n.node_id: n for n in self.root.all_nodes()}
        self._steps: List[StepSnapshot] = []
        self._call_stack: List[str] = []
        self._stack_node_ids: List[str] = []
        self._current_op_label: str = ""
        self._current_op_name: str = ""
        self._current_query_x: Optional[int] = None

    # ---- Snapshot & Query Utilities ----

    def snapshot_states(self) -> Dict[str, Tuple[Optional[int], Optional[int]]]:
        return {nid: (n.min, n.max) for nid, n in self.node_map.items()}

    def restore_states(self, states: Dict[str, Tuple[Optional[int], Optional[int]]]) -> None:
        for nid, (mn, mx) in states.items():
            if nid in self.node_map:
                self.node_map[nid].min = mn
                self.node_map[nid].max = mx

    def extract_elements(self, node: Optional[VEBNode] = None) -> Set[int]:
        if node is None:
            node = self.root
        if node.min is None:
            return set()
        elems: Set[int] = {node.min}
        if node.u <= 2:
            if node.max is not None:
                elems.add(node.max)
            return elems
        lower = lower_sqrt(node.u)
        for idx, cluster in enumerate(node.clusters):
            for val in self.extract_elements(cluster):
                elems.add(idx * lower + val)
        return elems

    def member_silent(self, x: int, node: Optional[VEBNode] = None) -> bool:
        if node is None:
            node = self.root
        if x == node.min or x == node.max:
            return True
        if node.u <= 2:
            return False
        return self.member_silent(node.low(x), node.clusters[node.high(x)])

    def _build_stack_edges(self) -> List[Tuple[str, str]]:
        edges: List[Tuple[str, str]] = []
        for i in range(len(self._stack_node_ids) - 1):
            edges.append((self._stack_node_ids[i], self._stack_node_ids[i + 1]))
        return edges

    def _record(
        self,
        node: VEBNode,
        line: int,
        explanation: str,
        variables: Dict[str, str],
        badge: str = "",
        extra_roles: Optional[Dict[str, str]] = None,
        field_highlights: Optional[Dict[str, Set[str]]] = None,
        active_edge: Optional[Tuple[str, str]] = None,
        in_flight_x: Optional[int] = None,
        result_val: Optional[str] = None,
        active_role: str = "active",
    ) -> None:
        roles: Dict[str, str] = {}
        for nid in self._stack_node_ids:
            roles[nid] = "stack"
        if extra_roles:
            roles.update(extra_roles)
        roles[node.node_id] = active_role

        fh: Dict[str, Set[str]] = {}
        if field_highlights:
            for k, v in field_highlights.items():
                fh[k] = set(v)

        snap = StepSnapshot(
            step_index=len(self._steps),
            op_label=self._current_op_label,
            op_name=self._current_op_name,
            active_line=line,
            active_node_id=node.node_id,
            node_states=self.snapshot_states(),
            node_roles=roles,
            field_highlights=fh,
            active_edge=active_edge,
            stack_edges=self._build_stack_edges(),
            call_stack=list(self._call_stack),
            variables=dict(variables),
            node_badge=badge,
            explanation=explanation,
            elements=self.extract_elements(),
            query_x=self._current_query_x,
            in_flight_x=in_flight_x,
            result_val=result_val,
        )
        self._steps.append(snap)

    def _begin_op(self, op_name: str, x: int) -> None:
        self._steps = []
        self._call_stack = []
        self._stack_node_ids = []
        self._current_op_name = op_name
        self._current_op_label = f"{op_name}({x})"
        self._current_query_x = x

    def make_idle_snapshot(self, message: str = "") -> StepSnapshot:
        elems = self.extract_elements()
        if not message:
            if elems:
                message = (
                    f"Ready (U = {self.u}). Currently storing {len(elems)} element(s): "
                    f"{sorted(elems)}. Choose an operation above to trace step by step."
                )
            else:
                message = (
                    f"Empty van Emde Boas Tree (U = {self.u}, valid keys 0..{self.u - 1}). "
                    f"Insert a key or click 'Demo: Guide Example' to start stepping!"
                )
        return StepSnapshot(
            step_index=0,
            op_label="Ready",
            op_name="insert",
            active_line=0,
            active_node_id="",
            node_states=self.snapshot_states(),
            node_roles={},
            field_highlights={},
            active_edge=None,
            stack_edges=[],
            call_stack=[],
            variables={"U": str(self.u), "count": str(len(elems))},
            node_badge="",
            explanation=message,
            elements=elems,
        )

    # ---- Public Instrumented Operations ----

    def run_insert(self, x: int) -> List[StepSnapshot]:
        self._begin_op("insert", x)
        if self.member_silent(x):
            self._record(
                self.root,
                line=1,
                explanation=(
                    f"Pre-check: {x} is ALREADY in the tree! "
                    f"Per vEB set rules (vEB_Tree_Guide.md Rule 3), duplicate values are skipped "
                    f"to preserve the lazy-min invariant."
                ),
                variables={"x": str(x), "status": "already present"},
                badge=f"skip dup {x}",
                active_role="found",
                result_val=f"{x} already in set",
            )
            return self._steps

        self._insert(self.root, x, is_root_call=True)
        return self._steps

    def _insert(self, tree: VEBNode, x: int, is_root_call: bool = False) -> None:
        frame = f"insert({tree.node_id} [U={tree.u}], x={x})"
        self._call_stack.append(frame)
        self._stack_node_ids.append(tree.node_id)

        def base_vars(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
            v = {
                "node": f"{tree.node_id} (U={tree.u})",
                "x": str(x),
                "tree.min": fmt_val(tree.min),
                "tree.max": fmt_val(tree.max),
            }
            if extra:
                v.update(extra)
            return v

        self._record(
            tree,
            line=1,
            explanation=f"Enter insert on {tree.node_id} (U={tree.u}) with x = {x}.",
            variables=base_vars(),
            badge=f"insert(x={x})",
            in_flight_x=x if is_root_call else None,
        )

        # Line 2: if (tree->min == NIL)
        self._record(
            tree,
            line=2,
            explanation=(
                f"Check if {tree.node_id} is empty: tree.min is {fmt_val(tree.min)}."
            ),
            variables=base_vars(),
            badge=f"min==NIL?",
            field_highlights={tree.node_id: {"min"}},
            in_flight_x=x if is_root_call else None,
        )
        if tree.min is None:
            tree.min = x
            tree.max = x
            self._record(
                tree,
                line=3,
                explanation=(
                    f"{tree.node_id} was empty! Call emptyInsert(tree, {x}): "
                    f"set min = {x} and max = {x} in O(1) time (no recursion needed)."
                ),
                variables=base_vars(),
                badge=f"emptyInsert({x})",
                field_highlights={tree.node_id: {"min", "max"}},
                active_role="updated",
            )
            self._record(
                tree,
                line=4,
                explanation=f"Return from insert({tree.node_id}, {x}).",
                variables=base_vars(),
                badge="return",
                active_role="returned",
                result_val="Inserted" if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return

        # Line 6: if (x < tree->min)
        self._record(
            tree,
            line=6,
            explanation=(
                f"Compare x ({x}) < tree.min ({tree.min}): "
                f"{'TRUE — must swap so smaller value stays lazily in min!' if x < tree.min else 'FALSE — keep current min.'}"
            ),
            variables=base_vars(),
            badge=f"{x} < {tree.min}?",
            field_highlights={tree.node_id: {"min"}},
            in_flight_x=x if is_root_call else None,
        )
        if x < tree.min:
            old_min = tree.min
            x, tree.min = old_min, x
            self._call_stack[-1] = f"insert({tree.node_id} [U={tree.u}], x={x}) [swapped]"
            self._record(
                tree,
                line=7,
                explanation=(
                    f"SWAP! Store smaller value {tree.min} directly in {tree.node_id}.min "
                    f"(min is NOT stored in clusters). Now push old min ({x}) downward instead!"
                ),
                variables=base_vars({"old_min": str(old_min), "new_x": str(x)}),
                badge=f"swap -> x={x}",
                field_highlights={tree.node_id: {"min"}},
                active_role="swap",
                in_flight_x=x if is_root_call else None,
            )

        # Line 9: if (tree->universeSize > 2)
        self._record(
            tree,
            line=9,
            explanation=(
                f"Check if {tree.node_id} has clusters: universeSize = {tree.u} "
                f"({'> 2, descend into clusters' if tree.u > 2 else '<= 2, base node — skip clusters'})."
            ),
            variables=base_vars(),
            badge=f"U={tree.u} > 2?",
            in_flight_x=x if is_root_call else None,
        )
        if tree.u > 2:
            h = tree.high(x)
            l = tree.low(x)
            lower = lower_sqrt(tree.u)
            self._record(
                tree,
                line=10,
                explanation=(
                    f"Split x = {x} using lowerSqrt({tree.u}) = {lower}: "
                    f"h = high({x}) = {x} // {lower} = {h} (Cluster {h}), "
                    f"l = low({x}) = {x} % {lower} = {l} (position {l})."
                ),
                variables=base_vars({"h": str(h), "l": str(l), "lowerSqrt": str(lower)}),
                badge=f"h={h}, l={l}",
                in_flight_x=x if is_root_call else None,
            )

            cluster = tree.clusters[h]
            self._record(
                tree,
                line=11,
                explanation=(
                    f"Inspect Cluster {h} ({cluster.node_id}): min is {fmt_val(cluster.min)}. "
                    f"{'Cluster is EMPTY! We will update summary(h) recursively and emptyInsert(l) in O(1).' if cluster.min is None else 'Cluster is NON-EMPTY! Summary already marks it, so only recurse into Cluster ' + str(h) + '.'}"
                ),
                variables=base_vars({"h": str(h), "l": str(l), f"C[{h}].min": fmt_val(cluster.min)}),
                badge=f"C[{h}].min==NIL?",
                extra_roles={cluster.node_id: "checked"},
                field_highlights={cluster.node_id: {"min"}},
                active_edge=(tree.node_id, cluster.node_id),
                in_flight_x=x if is_root_call else None,
            )
            if cluster.min is None:
                assert tree.summary is not None
                self._record(
                    tree,
                    line=12,
                    explanation=(
                        f"Cluster {h} was empty, so mark cluster index h = {h} as occupied in "
                        f"summary ({tree.summary.node_id}) via recursive insert(summary, {h})."
                    ),
                    variables=base_vars({"h": str(h), "l": str(l)}),
                    badge=f"-> summary({h})",
                    active_edge=(tree.node_id, tree.summary.node_id),
                    in_flight_x=x if is_root_call else None,
                )
                self._insert(tree.summary, h)

                cluster.min = l
                cluster.max = l
                self._record(
                    tree,
                    line=13,
                    explanation=(
                        f"Now call O(1) emptyInsert(clusters[{h}], {l}): sets {cluster.node_id}.min = {l} "
                        f"and max = {l} directly — NO second recursive call! This is why vEB is O(log log U)."
                    ),
                    variables=base_vars({"h": str(h), "l": str(l), f"C[{h}].min": str(l), f"C[{h}].max": str(l)}),
                    badge=f"C[{h}] <- {l}",
                    extra_roles={cluster.node_id: "updated"},
                    field_highlights={cluster.node_id: {"min", "max"}},
                    active_edge=(tree.node_id, cluster.node_id),
                )
            else:
                self._record(
                    tree,
                    line=15,
                    explanation=(
                        f"Cluster {h} already has elements (summary already knows about {h}). "
                        f"Recurse directly into clusters[{h}] ({cluster.node_id}) with l = {l}."
                    ),
                    variables=base_vars({"h": str(h), "l": str(l)}),
                    badge=f"-> C[{h}]({l})",
                    active_edge=(tree.node_id, cluster.node_id),
                    in_flight_x=x if is_root_call else None,
                )
                self._insert(cluster, l)

        # Line 18: if (x > tree->max)
        self._record(
            tree,
            line=18,
            explanation=(
                f"Check if x ({x}) > {tree.node_id}.max ({fmt_val(tree.max)}): "
                f"{'TRUE — update max!' if (tree.max is None or x > tree.max) else 'FALSE — max stays unchanged.'}"
            ),
            variables=base_vars(),
            badge=f"{x} > {fmt_val(tree.max)}?",
            field_highlights={tree.node_id: {"max"}},
        )
        if tree.max is None or x > tree.max:
            tree.max = x
            self._record(
                tree,
                line=19,
                explanation=f"Update {tree.node_id}.max = {x}.",
                variables=base_vars(),
                badge=f"max = {x}",
                field_highlights={tree.node_id: {"max"}},
                active_role="updated",
            )

        self._record(
            tree,
            line=21,
            explanation=(
                f"Done with insert({tree.node_id}, {x})."
                + (f" Key {self._current_query_x} is now stored in the vEB tree!" if is_root_call else "")
            ),
            variables=base_vars(),
            badge="done",
            active_role="found" if is_root_call else "returned",
            result_val=f"Inserted {self._current_query_x}" if is_root_call else None,
        )
        self._call_stack.pop()
        self._stack_node_ids.pop()

    def run_member(self, x: int) -> Tuple[bool, List[StepSnapshot]]:
        self._begin_op("member", x)
        res = self._member(self.root, x, is_root_call=True)
        return res, self._steps

    def _member(self, tree: VEBNode, x: int, is_root_call: bool = False) -> bool:
        frame = f"member({tree.node_id} [U={tree.u}], x={x})"
        self._call_stack.append(frame)
        self._stack_node_ids.append(tree.node_id)

        def base_vars(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
            v = {
                "node": f"{tree.node_id} (U={tree.u})",
                "x": str(x),
                "tree.min": fmt_val(tree.min),
                "tree.max": fmt_val(tree.max),
            }
            if extra:
                v.update(extra)
            return v

        self._record(
            tree,
            line=1,
            explanation=f"Enter member on {tree.node_id} (U={tree.u}) searching for x = {x}.",
            variables=base_vars(),
            badge=f"member({x})",
        )

        self._record(
            tree,
            line=2,
            explanation=(
                f"Check if x ({x}) matches tree.min ({fmt_val(tree.min)}) "
                f"or tree.max ({fmt_val(tree.max)})."
            ),
            variables=base_vars(),
            badge=f"x==min|max?",
            field_highlights={tree.node_id: {"min", "max"}},
        )
        if x == tree.min or x == tree.max:
            self._record(
                tree,
                line=3,
                explanation=f"MATCH! x = {x} equals {'min' if x == tree.min else 'max'} of {tree.node_id}. Return 1 (True).",
                variables=base_vars({"return": "1 (True)"}),
                badge="FOUND (1)",
                field_highlights={tree.node_id: {f for f, v in [("min", tree.min), ("max", tree.max)] if v == x}},
                active_role="found",
                result_val="True (1) — Found",
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return True

        self._record(
            tree,
            line=5,
            explanation=(
                f"No direct match at {tree.node_id}. Check base case: universeSize = {tree.u} "
                f"({'<= 2 -> cannot descend further' if tree.u <= 2 else '> 2 -> recurse into cluster'})."
            ),
            variables=base_vars(),
            badge=f"U={tree.u} <= 2?",
        )
        if tree.u <= 2:
            self._record(
                tree,
                line=6,
                explanation=f"Reached base node {tree.node_id} (U={tree.u}) without finding {x}. Return 0 (False).",
                variables=base_vars({"return": "0 (False)"}),
                badge="NOT FOUND (0)",
                active_role="not_found",
                result_val="False (0) — Not Found",
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return False

        h = tree.high(x)
        l = tree.low(x)
        lower = lower_sqrt(tree.u)
        cluster = tree.clusters[h]
        self._record(
            tree,
            line=8,
            explanation=(
                f"Compute cluster coordinates: h = {x} // {lower} = {h}, l = {x} % {lower} = {l}."
            ),
            variables=base_vars({"h": str(h), "l": str(l)}),
            badge=f"h={h}, l={l}",
        )
        self._record(
            tree,
            line=9,
            explanation=f"Recurse into Cluster {h} ({cluster.node_id}) to search for l = {l}.",
            variables=base_vars({"h": str(h), "l": str(l)}),
            badge=f"-> C[{h}]({l})",
            active_edge=(tree.node_id, cluster.node_id),
        )
        res = self._member(cluster, l)
        self._record(
            tree,
            line=9,
            explanation=(
                f"Cluster {h} returned {'1 (True)' if res else '0 (False)'}. "
                f"Propagate {'FOUND' if res else 'NOT FOUND'} up from {tree.node_id}."
            ),
            variables=base_vars({"h": str(h), "l": str(l), "return": "1 (True)" if res else "0 (False)"}),
            badge="ret 1" if res else "ret 0",
            active_role="found" if res else "not_found",
            result_val=("True (1) — Found" if res else "False (0) — Not Found") if is_root_call else None,
        )
        self._call_stack.pop()
        self._stack_node_ids.pop()
        return res

    def run_successor(self, x: int) -> Tuple[Optional[int], List[StepSnapshot]]:
        self._begin_op("successor", x)
        res = self._successor(self.root, x, is_root_call=True)
        return res, self._steps

    def _successor(self, tree: VEBNode, x: int, is_root_call: bool = False) -> Optional[int]:
        frame = f"successor({tree.node_id} [U={tree.u}], x={x})"
        self._call_stack.append(frame)
        self._stack_node_ids.append(tree.node_id)

        def base_vars(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
            v = {
                "node": f"{tree.node_id} (U={tree.u})",
                "x": str(x),
                "tree.min": fmt_val(tree.min),
                "tree.max": fmt_val(tree.max),
            }
            if extra:
                v.update(extra)
            return v

        self._record(
            tree,
            line=1,
            explanation=f"Enter successor on {tree.node_id} (U={tree.u}) looking for smallest element > {x}.",
            variables=base_vars(),
            badge=f"succ({x})",
        )

        # Base case U <= 2
        if tree.u <= 2:
            self._record(
                tree,
                line=2,
                explanation=f"Base case: {tree.node_id} has universeSize = {tree.u} <= 2.",
                variables=base_vars(),
                badge="base U=2",
                field_highlights={tree.node_id: {"max"}},
            )
            if x == 0 and tree.max == 1:
                self._record(
                    tree,
                    line=3,
                    explanation=f"x == 0 and {tree.node_id}.max == 1 -> successor is 1!",
                    variables=base_vars({"return": "1"}),
                    badge="ret 1",
                    field_highlights={tree.node_id: {"max"}},
                    active_role="found",
                    result_val="1" if is_root_call else None,
                )
                self._call_stack.pop()
                self._stack_node_ids.pop()
                return 1
            self._record(
                tree,
                line=4,
                explanation=(
                    f"Base check failed (x={x}, max={fmt_val(tree.max)}): no strictly greater key in {tree.node_id}. Return NIL."
                ),
                variables=base_vars({"return": "NIL"}),
                badge="ret NIL",
                active_role="not_found",
                result_val="NIL (-1)" if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return None

        # Check x < tree.min
        self._record(
            tree,
            line=6,
            explanation=(
                f"Check if x ({x}) < {tree.node_id}.min ({fmt_val(tree.min)}): "
                f"{'TRUE — tree.min is immediately the successor!' if (tree.min is not None and x < tree.min) else 'FALSE — successor (if any) must be in a cluster.'}"
            ),
            variables=base_vars(),
            badge=f"{x} < min?",
            field_highlights={tree.node_id: {"min"}},
        )
        if tree.min is not None and x < tree.min:
            ans = tree.min
            self._record(
                tree,
                line=7,
                explanation=f"Since x = {x} < min = {ans}, return tree.min = {ans} in O(1) time!",
                variables=base_vars({"return": str(ans)}),
                badge=f"ret {ans}",
                field_highlights={tree.node_id: {"min"}},
                active_role="found",
                result_val=str(ans) if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return ans

        h = tree.high(x)
        l = tree.low(x)
        lower = lower_sqrt(tree.u)
        self._record(
            tree,
            line=9,
            explanation=f"Split x = {x}: h = high({x}) = {h}, l = low({x}) = {l} (lowerSqrt = {lower}).",
            variables=base_vars({"h": str(h), "l": str(l)}),
            badge=f"h={h}, l={l}",
        )

        cluster = tree.clusters[h]
        max_low = cluster.max
        self._record(
            tree,
            line=10,
            explanation=f"Read maxLow = clusters[{h}].max = {fmt_val(max_low)} (from {cluster.node_id}).",
            variables=base_vars({"h": str(h), "l": str(l), "maxLow": fmt_val(max_low)}),
            badge=f"maxLow={fmt_val(max_low)}",
            extra_roles={cluster.node_id: "checked"},
            field_highlights={cluster.node_id: {"max"}},
            active_edge=(tree.node_id, cluster.node_id),
        )

        self._record(
            tree,
            line=11,
            explanation=(
                f"Check if successor is inside Cluster {h}: is maxLow ({fmt_val(max_low)}) != NIL and l ({l}) < maxLow? "
                f"{'YES! Successor is inside Cluster ' + str(h) + '.' if (max_low is not None and l < max_low) else 'NO — must jump to the next non-empty cluster using summary!'}"
            ),
            variables=base_vars({"h": str(h), "l": str(l), "maxLow": fmt_val(max_low)}),
            badge=f"l < maxLow?",
        )

        if max_low is not None and l < max_low:
            self._record(
                tree,
                line=12,
                explanation=f"Recurse into clusters[{h}] ({cluster.node_id}) to find successor of l = {l}.",
                variables=base_vars({"h": str(h), "l": str(l), "maxLow": str(max_low)}),
                badge=f"-> C[{h}]({l})",
                active_edge=(tree.node_id, cluster.node_id),
            )
            offset = self._successor(cluster, l)
            assert offset is not None
            ans = tree.index_of(h, offset)
            self._record(
                tree,
                line=13,
                explanation=(
                    f"Cluster {h} returned offset = {offset}. Rebuild value: "
                    f"indexOf({h}, {offset}) = {h} * {lower} + {offset} = {ans}."
                ),
                variables=base_vars({"h": str(h), "offset": str(offset), "return": str(ans)}),
                badge=f"ret {ans}",
                active_role="found",
                result_val=str(ans) if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return ans
        else:
            assert tree.summary is not None
            self._record(
                tree,
                line=15,
                explanation=(
                    f"No larger element in Cluster {h}. Ask summary ({tree.summary.node_id}) "
                    f"for successor(summary, {h}) to find the next non-empty cluster!"
                ),
                variables=base_vars({"h": str(h), "l": str(l), "maxLow": fmt_val(max_low)}),
                badge=f"-> summary({h})",
                active_edge=(tree.node_id, tree.summary.node_id),
            )
            succ_cluster = self._successor(tree.summary, h)
            if succ_cluster is None:
                self._record(
                    tree,
                    line=16,
                    explanation=f"summary returned succCluster = NIL: no non-empty cluster after Cluster {h}. Return NIL.",
                    variables=base_vars({"h": str(h), "succCluster": "NIL", "return": "NIL"}),
                    badge="ret NIL",
                    active_role="not_found",
                    result_val="NIL (-1)" if is_root_call else None,
                )
                self._call_stack.pop()
                self._stack_node_ids.pop()
                return None

            target_cluster = tree.clusters[succ_cluster]
            offset = target_cluster.min
            assert offset is not None
            self._record(
                tree,
                line=17,
                explanation=(
                    f"summary found next non-empty cluster: succCluster = {succ_cluster}! "
                    f"Read its minimum in O(1): offset = clusters[{succ_cluster}].min = {offset}."
                ),
                variables=base_vars({"succCluster": str(succ_cluster), "offset": str(offset)}),
                badge=f"C[{succ_cluster}].min={offset}",
                extra_roles={target_cluster.node_id: "found"},
                field_highlights={target_cluster.node_id: {"min"}},
                active_edge=(tree.node_id, target_cluster.node_id),
            )
            ans = tree.index_of(succ_cluster, offset)
            self._record(
                tree,
                line=18,
                explanation=(
                    f"Rebuild global value: indexOf({succ_cluster}, {offset}) = "
                    f"{succ_cluster} * {lower} + {offset} = {ans}. Return {ans}!"
                ),
                variables=base_vars({"succCluster": str(succ_cluster), "offset": str(offset), "return": str(ans)}),
                badge=f"ret {ans}",
                active_role="found",
                result_val=str(ans) if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return ans

    def run_predecessor(self, x: int) -> Tuple[Optional[int], List[StepSnapshot]]:
        self._begin_op("predecessor", x)
        res = self._predecessor(self.root, x, is_root_call=True)
        return res, self._steps

    def _predecessor(self, tree: VEBNode, x: int, is_root_call: bool = False) -> Optional[int]:
        frame = f"predecessor({tree.node_id} [U={tree.u}], x={x})"
        self._call_stack.append(frame)
        self._stack_node_ids.append(tree.node_id)

        def base_vars(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
            v = {
                "node": f"{tree.node_id} (U={tree.u})",
                "x": str(x),
                "tree.min": fmt_val(tree.min),
                "tree.max": fmt_val(tree.max),
            }
            if extra:
                v.update(extra)
            return v

        self._record(
            tree,
            line=1,
            explanation=f"Enter predecessor on {tree.node_id} (U={tree.u}) looking for largest element < {x}.",
            variables=base_vars(),
            badge=f"pred({x})",
        )

        if tree.u <= 2:
            self._record(
                tree,
                line=2,
                explanation=f"Base case: {tree.node_id} has universeSize = {tree.u} <= 2.",
                variables=base_vars(),
                badge="base U=2",
                field_highlights={tree.node_id: {"min"}},
            )
            if x == 1 and tree.min == 0:
                self._record(
                    tree,
                    line=3,
                    explanation=f"x == 1 and {tree.node_id}.min == 0 -> predecessor is 0!",
                    variables=base_vars({"return": "0"}),
                    badge="ret 0",
                    field_highlights={tree.node_id: {"min"}},
                    active_role="found",
                    result_val="0" if is_root_call else None,
                )
                self._call_stack.pop()
                self._stack_node_ids.pop()
                return 0
            self._record(
                tree,
                line=4,
                explanation=(
                    f"Base check failed (x={x}, min={fmt_val(tree.min)}): no strictly smaller key in {tree.node_id}. Return NIL."
                ),
                variables=base_vars({"return": "NIL"}),
                badge="ret NIL",
                active_role="not_found",
                result_val="NIL (-1)" if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return None

        self._record(
            tree,
            line=6,
            explanation=(
                f"Check if x ({x}) > {tree.node_id}.max ({fmt_val(tree.max)}): "
                f"{'TRUE — tree.max is immediately the predecessor!' if (tree.max is not None and x > tree.max) else 'FALSE — check clusters and summary.'}"
            ),
            variables=base_vars(),
            badge=f"{x} > max?",
            field_highlights={tree.node_id: {"max"}},
        )
        if tree.max is not None and x > tree.max:
            ans = tree.max
            self._record(
                tree,
                line=7,
                explanation=f"Since x = {x} > max = {ans}, return tree.max = {ans} in O(1) time!",
                variables=base_vars({"return": str(ans)}),
                badge=f"ret {ans}",
                field_highlights={tree.node_id: {"max"}},
                active_role="found",
                result_val=str(ans) if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return ans

        h = tree.high(x)
        l = tree.low(x)
        lower = lower_sqrt(tree.u)
        self._record(
            tree,
            line=9,
            explanation=f"Split x = {x}: h = high({x}) = {h}, l = low({x}) = {l} (lowerSqrt = {lower}).",
            variables=base_vars({"h": str(h), "l": str(l)}),
            badge=f"h={h}, l={l}",
        )

        cluster = tree.clusters[h]
        min_low = cluster.min
        self._record(
            tree,
            line=10,
            explanation=f"Read minLow = clusters[{h}].min = {fmt_val(min_low)} (from {cluster.node_id}).",
            variables=base_vars({"h": str(h), "l": str(l), "minLow": fmt_val(min_low)}),
            badge=f"minLow={fmt_val(min_low)}",
            extra_roles={cluster.node_id: "checked"},
            field_highlights={cluster.node_id: {"min"}},
            active_edge=(tree.node_id, cluster.node_id),
        )

        self._record(
            tree,
            line=11,
            explanation=(
                f"Check if predecessor is inside Cluster {h}: is minLow ({fmt_val(min_low)}) != NIL and l ({l}) > minLow? "
                f"{'YES! Predecessor is inside Cluster ' + str(h) + '.' if (min_low is not None and l > min_low) else 'NO — search earlier clusters via summary (and remember tree.min!).'}"
            ),
            variables=base_vars({"h": str(h), "l": str(l), "minLow": fmt_val(min_low)}),
            badge=f"l > minLow?",
        )

        if min_low is not None and l > min_low:
            self._record(
                tree,
                line=12,
                explanation=f"Recurse into clusters[{h}] ({cluster.node_id}) to find predecessor of l = {l}.",
                variables=base_vars({"h": str(h), "l": str(l), "minLow": str(min_low)}),
                badge=f"-> C[{h}]({l})",
                active_edge=(tree.node_id, cluster.node_id),
            )
            offset = self._predecessor(cluster, l)
            assert offset is not None
            ans = tree.index_of(h, offset)
            self._record(
                tree,
                line=13,
                explanation=(
                    f"Cluster {h} returned offset = {offset}. Rebuild value: "
                    f"indexOf({h}, {offset}) = {h} * {lower} + {offset} = {ans}."
                ),
                variables=base_vars({"h": str(h), "offset": str(offset), "return": str(ans)}),
                badge=f"ret {ans}",
                active_role="found",
                result_val=str(ans) if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return ans
        else:
            assert tree.summary is not None
            self._record(
                tree,
                line=15,
                explanation=(
                    f"No smaller element inside Cluster {h}. Ask summary ({tree.summary.node_id}) "
                    f"for predecessor(summary, {h}) to find the previous non-empty cluster."
                ),
                variables=base_vars({"h": str(h), "l": str(l), "minLow": fmt_val(min_low)}),
                badge=f"-> summary({h})",
                active_edge=(tree.node_id, tree.summary.node_id),
            )
            pred_cluster = self._predecessor(tree.summary, h)
            if pred_cluster is None:
                self._record(
                    tree,
                    line=16,
                    explanation=(
                        f"summary returned predCluster = NIL (no earlier non-empty cluster). "
                        f"Crucial check: since tree.min ({fmt_val(tree.min)}) isn't stored in clusters, check if x ({x}) > tree.min!"
                    ),
                    variables=base_vars({"predCluster": "NIL"}),
                    badge="check tree.min!",
                    field_highlights={tree.node_id: {"min"}},
                )
                if tree.min is not None and x > tree.min:
                    ans = tree.min
                    self._record(
                        tree,
                        line=17,
                        explanation=f"Yes! x ({x}) > {tree.node_id}.min ({ans}). Return tree.min = {ans}!",
                        variables=base_vars({"predCluster": "NIL", "return": str(ans)}),
                        badge=f"ret {ans}",
                        field_highlights={tree.node_id: {"min"}},
                        active_role="found",
                        result_val=str(ans) if is_root_call else None,
                    )
                    self._call_stack.pop()
                    self._stack_node_ids.pop()
                    return ans
                self._record(
                    tree,
                    line=18,
                    explanation=f"No smaller element exists anywhere in {tree.node_id}. Return NIL.",
                    variables=base_vars({"predCluster": "NIL", "return": "NIL"}),
                    badge="ret NIL",
                    active_role="not_found",
                    result_val="NIL (-1)" if is_root_call else None,
                )
                self._call_stack.pop()
                self._stack_node_ids.pop()
                return None

            target_cluster = tree.clusters[pred_cluster]
            offset = target_cluster.max
            assert offset is not None
            self._record(
                tree,
                line=20,
                explanation=(
                    f"summary found previous non-empty cluster: predCluster = {pred_cluster}! "
                    f"Read its maximum in O(1): offset = clusters[{pred_cluster}].max = {offset}."
                ),
                variables=base_vars({"predCluster": str(pred_cluster), "offset": str(offset)}),
                badge=f"C[{pred_cluster}].max={offset}",
                extra_roles={target_cluster.node_id: "found"},
                field_highlights={target_cluster.node_id: {"max"}},
                active_edge=(tree.node_id, target_cluster.node_id),
            )
            ans = tree.index_of(pred_cluster, offset)
            self._record(
                tree,
                line=21,
                explanation=(
                    f"Rebuild global value: indexOf({pred_cluster}, {offset}) = "
                    f"{pred_cluster} * {lower} + {offset} = {ans}. Return {ans}!"
                ),
                variables=base_vars({"predCluster": str(pred_cluster), "offset": str(offset), "return": str(ans)}),
                badge=f"ret {ans}",
                active_role="found",
                result_val=str(ans) if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return ans

    def run_delete(self, x: int) -> List[StepSnapshot]:
        self._begin_op("deleteVal", x)
        if not self.member_silent(x):
            self._record(
                self.root,
                line=1,
                explanation=(
                    f"Pre-check: {x} is NOT in the tree! "
                    f"Per vEB rules (vEB_Tree_Guide.md Rule 3), deleteVal requires x to exist first. Skipping delete."
                ),
                variables={"x": str(x), "status": "not in tree"},
                badge=f"missing {x}",
                active_role="not_found",
                result_val=f"{x} not found",
            )
            return self._steps

        self._delete(self.root, x, is_root_call=True)
        return self._steps

    def _delete(self, tree: VEBNode, x: int, is_root_call: bool = False) -> None:
        frame = f"deleteVal({tree.node_id} [U={tree.u}], x={x})"
        self._call_stack.append(frame)
        self._stack_node_ids.append(tree.node_id)

        def base_vars(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
            v = {
                "node": f"{tree.node_id} (U={tree.u})",
                "x": str(x),
                "tree.min": fmt_val(tree.min),
                "tree.max": fmt_val(tree.max),
            }
            if extra:
                v.update(extra)
            return v

        self._record(
            tree,
            line=1,
            explanation=f"Enter deleteVal on {tree.node_id} (U={tree.u}) removing x = {x}.",
            variables=base_vars(),
            badge=f"delete({x})",
        )

        # Single element in node
        self._record(
            tree,
            line=2,
            explanation=(
                f"Check if {tree.node_id} holds only 1 element: min ({fmt_val(tree.min)}) == max ({fmt_val(tree.max)})? "
                f"{'YES — clear both to NIL!' if tree.min == tree.max else 'NO — more than one element remains.'}"
            ),
            variables=base_vars(),
            badge="min==max?",
            field_highlights={tree.node_id: {"min", "max"}},
        )
        if tree.min == tree.max:
            tree.min = None
            tree.max = None
            self._record(
                tree,
                line=3,
                explanation=f"Only one element was in {tree.node_id}. Set min = NIL, max = NIL and return.",
                variables=base_vars(),
                badge="cleared NIL",
                field_highlights={tree.node_id: {"min", "max"}},
                active_role="updated",
                result_val=f"Deleted {self._current_query_x}" if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return

        # Base case U <= 2 with 2 elements (0 and 1)
        if tree.u <= 2:
            self._record(
                tree,
                line=5,
                explanation=f"Base node {tree.node_id} (U=2) has both 0 and 1. Removing x = {x}.",
                variables=base_vars(),
                badge="base U=2",
            )
            remaining = 1 if x == 0 else 0
            tree.min = remaining
            tree.max = remaining
            self._record(
                tree,
                line=7,
                explanation=f"Keep the other element ({remaining}): set min = max = {remaining} and return.",
                variables=base_vars(),
                badge=f"keep {remaining}",
                field_highlights={tree.node_id: {"min", "max"}},
                active_role="updated",
                result_val=f"Deleted {self._current_query_x}" if is_root_call else None,
            )
            self._call_stack.pop()
            self._stack_node_ids.pop()
            return

        # If deleting min, promote smallest element from clusters to min
        self._record(
            tree,
            line=9,
            explanation=(
                f"Check if deleting tree.min: is x ({x}) == {tree.node_id}.min ({tree.min})? "
                f"{'YES! Must promote the next smallest element from clusters into min.' if x == tree.min else 'NO — proceed directly to cluster deletion.'}"
            ),
            variables=base_vars(),
            badge=f"x == min?",
            field_highlights={tree.node_id: {"min"}},
        )
        if x == tree.min:
            assert tree.summary is not None
            first_cluster = tree.summary.min
            assert first_cluster is not None
            self._record(
                tree,
                line=10,
                explanation=(
                    f"Look up first non-empty cluster in summary ({tree.summary.node_id}): "
                    f"firstCluster = summary.min = {first_cluster}."
                ),
                variables=base_vars({"firstCluster": str(first_cluster)}),
                badge=f"firstC = {first_cluster}",
                extra_roles={tree.summary.node_id: "checked"},
                field_highlights={tree.summary.node_id: {"min"}},
                active_edge=(tree.node_id, tree.summary.node_id),
            )
            c_node = tree.clusters[first_cluster]
            assert c_node.min is not None
            promoted = tree.index_of(first_cluster, c_node.min)
            x = promoted
            tree.min = x
            self._call_stack[-1] = f"deleteVal({tree.node_id} [U={tree.u}], x={x}) [promoted]"
            self._record(
                tree,
                line=12,
                explanation=(
                    f"Promote smallest cluster value: x = indexOf({first_cluster}, clusters[{first_cluster}].min={c_node.min}) = {x}. "
                    f"Set {tree.node_id}.min = {x}. Now delete duplicate {x} from Cluster {first_cluster}."
                ),
                variables=base_vars({"firstCluster": str(first_cluster), "promoted_x": str(x)}),
                badge=f"min <- {x}",
                extra_roles={c_node.node_id: "checked"},
                field_highlights={tree.node_id: {"min"}, c_node.node_id: {"min"}},
                active_edge=(tree.node_id, c_node.node_id),
                active_role="swap",
            )

        h = tree.high(x)
        l = tree.low(x)
        lower = lower_sqrt(tree.u)
        cluster = tree.clusters[h]
        self._record(
            tree,
            line=14,
            explanation=f"Split x = {x}: h = {x} // {lower} = {h}, l = {x} % {lower} = {l}.",
            variables=base_vars({"h": str(h), "l": str(l)}),
            badge=f"h={h}, l={l}",
        )
        self._record(
            tree,
            line=15,
            explanation=f"Recursively delete l = {l} from clusters[{h}] ({cluster.node_id}).",
            variables=base_vars({"h": str(h), "l": str(l)}),
            badge=f"-> del C[{h}]({l})",
            active_edge=(tree.node_id, cluster.node_id),
        )
        self._delete(cluster, l)

        # Check if cluster became empty
        self._record(
            tree,
            line=16,
            explanation=(
                f"After deleting {l} from Cluster {h}, check if {cluster.node_id} became empty: "
                f"min is {fmt_val(cluster.min)}."
            ),
            variables=base_vars({"h": str(h), "l": str(l), f"C[{h}].min": fmt_val(cluster.min)}),
            badge=f"C[{h}] empty?",
            extra_roles={cluster.node_id: "checked"},
            field_highlights={cluster.node_id: {"min"}},
            active_edge=(tree.node_id, cluster.node_id),
        )
        if cluster.min is None:
            assert tree.summary is not None
            self._record(
                tree,
                line=17,
                explanation=(
                    f"Cluster {h} is now EMPTY! Remove cluster index {h} from summary ({tree.summary.node_id}). "
                    f"(Note: the previous cluster delete was O(1) because it held only 1 element!)"
                ),
                variables=base_vars({"h": str(h)}),
                badge=f"-> del sum({h})",
                active_edge=(tree.node_id, tree.summary.node_id),
            )
            self._delete(tree.summary, h)

            self._record(
                tree,
                line=18,
                explanation=(
                    f"Check if deleted x ({x}) was {tree.node_id}.max ({fmt_val(tree.max)}): "
                    f"{'YES — recompute max via summary.max!' if x == tree.max else 'NO — max stays valid.'}"
                ),
                variables=base_vars({"h": str(h)}),
                badge="x == max?",
                field_highlights={tree.node_id: {"max"}},
            )
            if x == tree.max:
                summary_max = tree.summary.max
                self._record(
                    tree,
                    line=19,
                    explanation=f"Read summaryMax = summary.max = {fmt_val(summary_max)}.",
                    variables=base_vars({"summaryMax": fmt_val(summary_max)}),
                    badge=f"sumMax={fmt_val(summary_max)}",
                    extra_roles={tree.summary.node_id: "checked"},
                    field_highlights={tree.summary.node_id: {"max"}},
                    active_edge=(tree.node_id, tree.summary.node_id),
                )
                if summary_max is None:
                    tree.max = tree.min
                    self._record(
                        tree,
                        line=20,
                        explanation=f"All clusters are now empty (summaryMax == NIL)! Only tree.min ({tree.min}) remains -> set max = min = {tree.min}.",
                        variables=base_vars({"summaryMax": "NIL"}),
                        badge=f"max = {tree.max}",
                        field_highlights={tree.node_id: {"min", "max"}},
                        active_role="updated",
                    )
                else:
                    last_c = tree.clusters[summary_max]
                    assert last_c.max is not None
                    tree.max = tree.index_of(summary_max, last_c.max)
                    self._record(
                        tree,
                        line=21,
                        explanation=(
                            f"Set {tree.node_id}.max = indexOf({summary_max}, clusters[{summary_max}].max={last_c.max}) = {tree.max}."
                        ),
                        variables=base_vars({"summaryMax": str(summary_max), "new_max": str(tree.max)}),
                        badge=f"max = {tree.max}",
                        extra_roles={last_c.node_id: "checked"},
                        field_highlights={tree.node_id: {"max"}, last_c.node_id: {"max"}},
                        active_edge=(tree.node_id, last_c.node_id),
                        active_role="updated",
                    )
        elif x == tree.max:
            assert cluster.max is not None
            tree.max = tree.index_of(h, cluster.max)
            self._record(
                tree,
                line=24,
                explanation=(
                    f"Cluster {h} still has elements, and deleted x ({x}) was {tree.node_id}.max. "
                    f"Update max = indexOf({h}, clusters[{h}].max={cluster.max}) = {tree.max}."
                ),
                variables=base_vars({"h": str(h), "new_max": str(tree.max)}),
                badge=f"max = {tree.max}",
                extra_roles={cluster.node_id: "checked"},
                field_highlights={tree.node_id: {"max"}, cluster.node_id: {"max"}},
                active_edge=(tree.node_id, cluster.node_id),
                active_role="updated",
            )

        self._record(
            tree,
            line=26,
            explanation=(
                f"Done with deleteVal({tree.node_id}, {x})."
                + (f" Key {self._current_query_x} removed!" if is_root_call else "")
            ),
            variables=base_vars(),
            badge="done",
            active_role="found" if is_root_call else "returned",
            result_val=f"Deleted {self._current_query_x}" if is_root_call else None,
        )
        self._call_stack.pop()
        self._stack_node_ids.pop()


# ---------------------------------------------------------------------------
# Tree Layout Calculator (Non-overlapping bottom-up layout)
# ---------------------------------------------------------------------------

@dataclass
class NodeLayout:
    x: float  # center x
    y: float  # center y
    w: float
    h: float


def compute_tree_layout(root: VEBNode) -> Tuple[Dict[str, NodeLayout], Tuple[float, float, float, float]]:
    """Compute non-overlapping coordinates for every node in the vEB tree."""
    LEAF_W, LEAF_H = 82.0, 54.0
    INT_W, INT_H = 116.0, 62.0
    H_GAP = 10.0
    SUMMARY_GAP = 22.0
    V_GAP = 64.0

    widths: Dict[str, float] = {}
    sizes: Dict[str, Tuple[float, float]] = {}

    def measure(node: VEBNode) -> float:
        if node.u <= 2:
            sizes[node.node_id] = (LEAF_W, LEAF_H)
            widths[node.node_id] = LEAF_W
            return LEAF_W
        sizes[node.node_id] = (INT_W, INT_H)
        assert node.summary is not None
        sw = measure(node.summary)
        cws = [measure(c) for c in node.clusters]
        children_total = sw + SUMMARY_GAP + sum(cws) + H_GAP * max(0, len(cws) - 1)
        total = max(INT_W, children_total)
        widths[node.node_id] = total
        return total

    measure(root)
    layouts: Dict[str, NodeLayout] = {}

    def place(node: VEBNode, left_x: float, top_y: float) -> None:
        w, h = sizes[node.node_id]
        span = widths[node.node_id]
        cx = left_x + span / 2.0
        cy = top_y + h / 2.0
        layouts[node.node_id] = NodeLayout(x=cx, y=cy, w=w, h=h)

        if node.u <= 2:
            return

        assert node.summary is not None
        child_y = top_y + h + V_GAP
        cws = [widths[c.node_id] for c in node.clusters]
        sw = widths[node.summary.node_id]
        children_total = sw + SUMMARY_GAP + sum(cws) + H_GAP * max(0, len(cws) - 1)
        cursor_x = left_x + (span - children_total) / 2.0

        place(node.summary, cursor_x, child_y)
        cursor_x += sw + SUMMARY_GAP
        for c, cw in zip(node.clusters, cws):
            place(c, cursor_x, child_y)
            cursor_x += cw + H_GAP

    place(root, 40.0, 48.0)

    min_x = min(l.x - l.w / 2 for l in layouts.values()) - 40
    min_y = min(l.y - l.h / 2 for l in layouts.values()) - 48
    max_x = max(l.x + l.w / 2 for l in layouts.values()) + 40
    max_y = max(l.y + l.h / 2 for l in layouts.values()) + 40
    return layouts, (min_x, min_y, max_x, max_y)


# ---------------------------------------------------------------------------
# Color Palette (Dark Modern IDE Theme)
# ---------------------------------------------------------------------------

THEME = {
    "bg": "#0f172a",
    "panel": "#1e293b",
    "panel_alt": "#162032",
    "surface": "#263348",
    "border": "#334155",
    "border_light": "#475569",
    "text": "#f1f5f9",
    "text_dim": "#94a3b8",
    "text_muted": "#64748b",
    "canvas_bg": "#0b1120",
    "grid_dot": "#1e293b",
    # Node / Role Accents
    "summary_hdr": "#581c87",
    "summary_border": "#a855f7",
    "summary_edge": "#7e22ce",
    "cluster_hdr": "#1e3a5f",
    "cluster_border": "#3b82f6",
    "cluster_edge": "#334155",
    "root_hdr": "#0f4c5c",
    "empty_bg": "#111827",
    "occupied_bg": "#1e293b",
    # Step Highlights
    "active": "#38bdf8",
    "stack": "#818cf8",
    "updated": "#f59e0b",
    "swap": "#f472b6",
    "found": "#34d399",
    "not_found": "#f87171",
    "checked": "#facc15",
    "returned": "#2dd4bf",
    # Buttons
    "btn_insert": "#059669",
    "btn_delete": "#dc2626",
    "btn_member": "#0284c7",
    "btn_succ": "#d97706",
    "btn_pred": "#7c3aed",
    "btn_neutral": "#334155",
}


# ---------------------------------------------------------------------------
# Main Interactive GUI Application
# ---------------------------------------------------------------------------

class VEBVisualizerApp:
    def __init__(self, root_tk: tk.Tk):
        self.tk = root_tk
        self.tk.title("van Emde Boas (vEB) Tree — Interactive Step-by-Step Visualizer")
        self.tk.geometry("1420x860")
        self.tk.minsize(1060, 680)
        self.tk.configure(bg=THEME["bg"])

        # Core state
        self.universe_var = tk.StringVar(value="16")
        self.x_var = tk.StringVar(value="7")
        self.speed_var = tk.IntVar(value=650)  # ms per step
        self.auto_follow_var = tk.BooleanVar(value=True)

        self.engine = VEBEngine(16)
        self.layouts, self.bounds = compute_tree_layout(self.engine.root)
        self.trace: List[StepSnapshot] = [self.engine.make_idle_snapshot()]
        self.step_idx: int = 0
        self.is_playing: bool = False
        self._play_after_id: Optional[str] = None

        # Canvas camera transform (world -> screen: sx = wx * zoom + pan_x)
        self.zoom: float = 1.0
        self.pan_x: float = 0.0
        self.pan_y: float = 0.0
        self._drag_start: Optional[Tuple[int, int]] = None
        self._selected_node_id: Optional[str] = None
        self._suppress_slider: bool = False

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()

        # Fit canvas once window renders
        self.tk.after(80, self._initial_fit_and_render)

    def _configure_styles(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=THEME["bg"])
        style.configure("Panel.TFrame", background=THEME["panel"])
        style.configure("TLabel", background=THEME["bg"], foreground=THEME["text"], font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=THEME["panel"], foreground=THEME["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=THEME["panel"], foreground=THEME["text_dim"], font=("Segoe UI", 9))
        style.configure("TPanedwindow", background=THEME["border"])
        style.configure("TNotebook", background=THEME["panel"], borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background=THEME["surface"],
            foreground=THEME["text_dim"],
            padding=(10, 4),
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["panel_alt"])],
            foreground=[("selected", THEME["active"])],
        )

    def _make_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        bg: str = THEME["btn_neutral"],
        fg: str = "#ffffff",
        padx: int = 10,
        pady: int = 5,
        font=("Segoe UI", 9, "bold"),
    ) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=THEME["border_light"],
            activeforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            padx=padx,
            pady=pady,
            cursor="hand2",
            font=font,
        )

    def _build_ui(self) -> None:
        # ---- TOP CONTROL BAR ----
        top_bar = tk.Frame(self.tk, bg=THEME["panel"], highlightbackground=THEME["border"], highlightthickness=1)
        top_bar.pack(side=tk.TOP, fill=tk.X)

        # Row 1: Title + Universe + Operation Input + Action Buttons
        row1 = tk.Frame(top_bar, bg=THEME["panel"])
        row1.pack(side=tk.TOP, fill=tk.X, padx=12, pady=8)

        tk.Label(
            row1,
            text="vEB Tree Visualizer",
            bg=THEME["panel"],
            fg=THEME["active"],
            font=("Segoe UI", 13, "bold"),
        ).pack(side=tk.LEFT, padx=(0, 14))

        # Universe selector
        tk.Label(row1, text="Universe U:", bg=THEME["panel"], fg=THEME["text_dim"], font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        u_menu = ttk.Combobox(
            row1,
            textvariable=self.universe_var,
            values=["4", "8", "16", "32", "64"],
            width=4,
            state="readonly",
            font=("Consolas", 10, "bold"),
        )
        u_menu.pack(side=tk.LEFT, padx=(0, 6))
        u_menu.bind("<<ComboboxSelected>>", lambda _e: self.on_change_universe())

        self._make_button(row1, "Reset", self.on_reset, bg=THEME["btn_neutral"], padx=8, pady=4).pack(
            side=tk.LEFT, padx=(0, 14)
        )

        # Separator
        tk.Frame(row1, width=2, height=24, bg=THEME["border"]).pack(side=tk.LEFT, padx=(0, 14))

        # x input
        tk.Label(row1, text="Key x:", bg=THEME["panel"], fg=THEME["text_dim"], font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self.x_entry = tk.Entry(
            row1,
            textvariable=self.x_var,
            width=5,
            bg=THEME["canvas_bg"],
            fg=THEME["text"],
            insertbackground=THEME["active"],
            relief=tk.FLAT,
            highlightbackground=THEME["border_light"],
            highlightthickness=1,
            font=("Consolas", 11, "bold"),
            justify=tk.CENTER,
        )
        self.x_entry.pack(side=tk.LEFT, padx=(0, 8), ipady=2)
        self.x_entry.bind("<Return>", lambda _e: self.on_operation("insert"))

        # Operation buttons
        self._make_button(row1, "+ Insert", lambda: self.on_operation("insert"), bg=THEME["btn_insert"]).pack(
            side=tk.LEFT, padx=3
        )
        self._make_button(row1, "- Delete", lambda: self.on_operation("deleteVal"), bg=THEME["btn_delete"]).pack(
            side=tk.LEFT, padx=3
        )
        self._make_button(row1, "? Member", lambda: self.on_operation("member"), bg=THEME["btn_member"]).pack(
            side=tk.LEFT, padx=3
        )
        self._make_button(row1, "> Successor", lambda: self.on_operation("successor"), bg=THEME["btn_succ"]).pack(
            side=tk.LEFT, padx=3
        )
        self._make_button(row1, "< Predecessor", lambda: self.on_operation("predecessor"), bg=THEME["btn_pred"]).pack(
            side=tk.LEFT, padx=3
        )

        # Right side presets & script runner
        right_btns = tk.Frame(row1, bg=THEME["panel"])
        right_btns.pack(side=tk.RIGHT)

        self._make_button(
            right_btns, "Script / Batch...", self.open_script_dialog, bg="#0f766e", padx=9
        ).pack(side=tk.RIGHT, padx=3)
        self._make_button(
            right_btns, "Random Fill", self.on_random_fill, bg=THEME["surface"], padx=9
        ).pack(side=tk.RIGHT, padx=3)
        self._make_button(
            right_btns, "Demo: Guide {2,3,7,14,15}", self.on_demo_guide, bg="#4338ca", padx=9
        ).pack(side=tk.RIGHT, padx=3)

        # ---- MAIN SPLIT WORKSPACE ----
        paned = tk.PanedWindow(
            self.tk,
            orient=tk.HORIZONTAL,
            bg=THEME["border"],
            sashwidth=5,
            sashrelief=tk.FLAT,
            bd=0,
        )
        paned.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # LEFT: Universe Strip + Interactive Tree Canvas + Canvas Toolbar
        left_frame = tk.Frame(paned, bg=THEME["bg"])
        paned.add(left_frame, minsize=560, stretch="always")

        # Universe strip
        strip_header = tk.Frame(left_frame, bg=THEME["panel_alt"])
        strip_header.pack(side=tk.TOP, fill=tk.X)
        self.strip_info_label = tk.Label(
            strip_header,
            text="Universe [0..15] — Stored Set: { }",
            bg=THEME["panel_alt"],
            fg=THEME["text_dim"],
            font=("Consolas", 9, "bold"),
            anchor="w",
        )
        self.strip_info_label.pack(side=tk.LEFT, padx=10, pady=(4, 0))

        self.result_badge_label = tk.Label(
            strip_header,
            text="",
            bg=THEME["panel_alt"],
            fg=THEME["found"],
            font=("Segoe UI", 9, "bold"),
            anchor="e",
        )
        self.result_badge_label.pack(side=tk.RIGHT, padx=10, pady=(4, 0))

        self.strip_canvas = tk.Canvas(
            left_frame,
            height=46,
            bg=THEME["panel_alt"],
            highlightthickness=0,
            bd=0,
        )
        self.strip_canvas.pack(side=tk.TOP, fill=tk.X)
        self.strip_canvas.bind("<Configure>", lambda _e: self.render_universe_strip())
        self.strip_canvas.bind("<Button-1>", self.on_strip_click)

        # Main Tree Canvas
        self.canvas = tk.Canvas(
            left_frame,
            bg=THEME["canvas_bg"],
            highlightthickness=0,
            bd=0,
            cursor="fleur",
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<MouseWheel>", self.on_canvas_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._zoom_at(e.x, e.y, 1.15))
        self.canvas.bind("<Button-5>", lambda e: self._zoom_at(e.x, e.y, 1 / 1.15))
        self.canvas.bind("<Configure>", lambda _e: self.render_tree())

        # Canvas Utility / Legend Bar
        canvas_bar = tk.Frame(left_frame, bg=THEME["panel_alt"], height=30)
        canvas_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self._make_button(canvas_bar, "Zoom -", lambda: self.zoom_center(1 / 1.2), bg=THEME["surface"], padx=7, pady=2, font=("Segoe UI", 8, "bold")).pack(
            side=tk.LEFT, padx=(8, 2), pady=3
        )
        self._make_button(canvas_bar, "Zoom +", lambda: self.zoom_center(1.2), bg=THEME["surface"], padx=7, pady=2, font=("Segoe UI", 8, "bold")).pack(
            side=tk.LEFT, padx=2, pady=3
        )
        self._make_button(canvas_bar, "Fit View", self.fit_to_view, bg=THEME["surface"], padx=7, pady=2, font=("Segoe UI", 8, "bold")).pack(
            side=tk.LEFT, padx=2, pady=3
        )
        self._make_button(canvas_bar, "Focus Active", self.focus_active_node, bg=THEME["surface"], padx=7, pady=2, font=("Segoe UI", 8, "bold")).pack(
            side=tk.LEFT, padx=2, pady=3
        )

        tk.Checkbutton(
            canvas_bar,
            text="Auto-follow",
            variable=self.auto_follow_var,
            bg=THEME["panel_alt"],
            fg=THEME["text_dim"],
            selectcolor=THEME["canvas_bg"],
            activebackground=THEME["panel_alt"],
            activeforeground=THEME["text"],
            font=("Segoe UI", 8),
        ).pack(side=tk.LEFT, padx=(8, 12))

        # Legend pills
        legend_items = [
            ("Active", THEME["active"]),
            ("Summary", THEME["summary_border"]),
            ("Updated", THEME["updated"]),
            ("Swap", THEME["swap"]),
            ("Found", THEME["found"]),
            ("NIL/Miss", THEME["not_found"]),
        ]
        for lbl, col in legend_items:
            f = tk.Frame(canvas_bar, bg=THEME["panel_alt"])
            f.pack(side=tk.RIGHT, padx=5)
            tk.Label(f, text="●", bg=THEME["panel_alt"], fg=col, font=("Segoe UI", 10)).pack(side=tk.LEFT)
            tk.Label(f, text=lbl, bg=THEME["panel_alt"], fg=THEME["text_dim"], font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(1, 0))

        self.node_inspect_label = tk.Label(
            canvas_bar,
            text="Tip: click any universe cell to fill Key x, or click any tree node to inspect it",
            bg=THEME["panel_alt"],
            fg=THEME["text_muted"],
            font=("Segoe UI", 8),
        )
        self.node_inspect_label.pack(side=tk.LEFT, padx=6)

        # RIGHT: Step Narration + Live Code + Variables/Call Stack/Step Log
        right_frame = tk.Frame(paned, bg=THEME["panel"])
        paned.add(right_frame, minsize=360, width=440)

        # 1. Step Narration Card
        narration_box = tk.Frame(right_frame, bg=THEME["panel_alt"], highlightbackground=THEME["border"], highlightthickness=1)
        narration_box.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(8, 6))

        nar_hdr = tk.Frame(narration_box, bg=THEME["panel_alt"])
        nar_hdr.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(6, 2))

        self.op_badge_lbl = tk.Label(
            nar_hdr,
            text="READY",
            bg=THEME["surface"],
            fg=THEME["active"],
            font=("Consolas", 9, "bold"),
            padx=7,
            pady=2,
        )
        self.op_badge_lbl.pack(side=tk.LEFT)

        self.step_counter_lbl = tk.Label(
            nar_hdr,
            text="Step 0 / 0",
            bg=THEME["panel_alt"],
            fg=THEME["text_dim"],
            font=("Consolas", 9, "bold"),
        )
        self.step_counter_lbl.pack(side=tk.RIGHT)

        self.explanation_text = tk.Text(
            narration_box,
            height=4,
            wrap=tk.WORD,
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            relief=tk.FLAT,
            bd=0,
            font=("Segoe UI", 10),
            padx=10,
            pady=4,
            state=tk.DISABLED,
        )
        self.explanation_text.pack(side=tk.TOP, fill=tk.X, pady=(0, 6))

        # 2. Live Algorithm Code Viewer
        code_container = tk.Frame(right_frame, bg=THEME["panel_alt"], highlightbackground=THEME["border"], highlightthickness=1)
        code_container.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 6))

        code_hdr = tk.Frame(code_container, bg=THEME["surface"])
        code_hdr.pack(side=tk.TOP, fill=tk.X)
        self.code_title_lbl = tk.Label(
            code_hdr,
            text="Execution Trace — vanEmdeBoasTrees.h",
            bg=THEME["surface"],
            fg=THEME["text"],
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            padx=8,
            pady=4,
        )
        self.code_title_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        code_scroll = ttk.Scrollbar(code_container, orient=tk.VERTICAL)
        code_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.code_text = tk.Text(
            code_container,
            wrap=tk.NONE,
            bg=THEME["canvas_bg"],
            fg=THEME["text_dim"],
            relief=tk.FLAT,
            bd=0,
            font=("Consolas", 9),
            padx=6,
            pady=6,
            yscrollcommand=code_scroll.set,
            state=tk.DISABLED,
            height=15,
        )
        self.code_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        code_scroll.config(command=self.code_text.yview)
        self.code_text.tag_configure("active_line", background="#1e3a5f", foreground="#ffffff", font=("Consolas", 9, "bold"))
        self.code_text.tag_configure("lineno", foreground=THEME["text_muted"])
        self.code_text.tag_configure("arrow", foreground=THEME["active"], font=("Consolas", 9, "bold"))

        # 3. Bottom Inspector Tabs (Variables & Call Stack | Step Log)
        tabs = ttk.Notebook(right_frame)
        tabs.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=False, padx=8, pady=(0, 8))

        # Tab 1: Variables + Call Stack
        state_tab = tk.Frame(tabs, bg=THEME["panel_alt"])
        tabs.add(state_tab, text="Variables & Call Stack")

        tk.Label(
            state_tab,
            text="Local Variables",
            bg=THEME["panel_alt"],
            fg=THEME["text_dim"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(side=tk.TOP, fill=tk.X, padx=8, pady=(6, 2))

        self.vars_frame = tk.Frame(state_tab, bg=THEME["panel_alt"])
        self.vars_frame.pack(side=tk.TOP, fill=tk.X, padx=8, pady=(0, 6))

        tk.Label(
            state_tab,
            text="Recursion Call Stack (top -> active)",
            bg=THEME["panel_alt"],
            fg=THEME["text_dim"],
            font=("Segoe UI", 8, "bold"),
            anchor="w",
        ).pack(side=tk.TOP, fill=tk.X, padx=8, pady=(2, 2))

        self.stack_listbox = tk.Listbox(
            state_tab,
            height=5,
            bg=THEME["canvas_bg"],
            fg=THEME["text"],
            selectbackground=THEME["surface"],
            relief=tk.FLAT,
            bd=0,
            font=("Consolas", 9),
            highlightthickness=0,
        )
        self.stack_listbox.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        # Tab 2: Full Step Log (click any step to jump)
        log_tab = tk.Frame(tabs, bg=THEME["panel_alt"])
        tabs.add(log_tab, text="All Steps (Click to Jump)")

        log_scroll = ttk.Scrollbar(log_tab, orient=tk.VERTICAL)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.step_listbox = tk.Listbox(
            log_tab,
            height=9,
            bg=THEME["canvas_bg"],
            fg=THEME["text_dim"],
            selectbackground="#1e3a5f",
            selectforeground="#ffffff",
            relief=tk.FLAT,
            bd=0,
            font=("Consolas", 8),
            yscrollcommand=log_scroll.set,
            highlightthickness=0,
        )
        self.step_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)
        log_scroll.config(command=self.step_listbox.yview)
        self.step_listbox.bind("<<ListboxSelect>>", self.on_step_list_select)

        # ---- BOTTOM STEP PLAYBACK BAR ----
        bottom_bar = tk.Frame(self.tk, bg=THEME["panel"], highlightbackground=THEME["border"], highlightthickness=1)
        bottom_bar.pack(side=tk.BOTTOM, fill=tk.X)

        ctrl_row = tk.Frame(bottom_bar, bg=THEME["panel"])
        ctrl_row.pack(side=tk.TOP, fill=tk.X, padx=12, pady=7)

        self._make_button(ctrl_row, "|< First", self.step_first, bg=THEME["surface"], padx=9).pack(side=tk.LEFT, padx=2)
        self._make_button(ctrl_row, "< Prev", self.step_prev, bg=THEME["surface"], padx=10).pack(side=tk.LEFT, padx=2)
        self.play_btn = self._make_button(ctrl_row, "▶ Play", self.toggle_play, bg=THEME["btn_member"], padx=14)
        self.play_btn.pack(side=tk.LEFT, padx=4)
        self._make_button(ctrl_row, "Next >", self.step_next, bg=THEME["surface"], padx=10).pack(side=tk.LEFT, padx=2)
        self._make_button(ctrl_row, "Last >|", self.step_last, bg=THEME["surface"], padx=9).pack(side=tk.LEFT, padx=2)

        # Timeline Scrubber
        self.step_scale = tk.Scale(
            ctrl_row,
            from_=0,
            to=0,
            orient=tk.HORIZONTAL,
            showvalue=False,
            bg=THEME["panel"],
            fg=THEME["text"],
            troughcolor=THEME["canvas_bg"],
            activebackground=THEME["active"],
            highlightthickness=0,
            bd=0,
            command=self.on_slider_move,
        )
        self.step_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=14)

        # Speed slider
        tk.Label(ctrl_row, text="Speed:", bg=THEME["panel"], fg=THEME["text_dim"], font=("Segoe UI", 9, "bold")).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        tk.Label(ctrl_row, text="Fast", bg=THEME["panel"], fg=THEME["text_muted"], font=("Segoe UI", 8)).pack(side=tk.LEFT)
        speed_scale = tk.Scale(
            ctrl_row,
            from_=150,
            to=1800,
            resolution=50,
            variable=self.speed_var,
            orient=tk.HORIZONTAL,
            showvalue=False,
            length=110,
            bg=THEME["panel"],
            troughcolor=THEME["canvas_bg"],
            activebackground=THEME["active"],
            highlightthickness=0,
            bd=0,
        )
        speed_scale.pack(side=tk.LEFT, padx=3)
        tk.Label(ctrl_row, text="Slow", bg=THEME["panel"], fg=THEME["text_muted"], font=("Segoe UI", 8)).pack(
            side=tk.LEFT, padx=(0, 8)
        )

        tk.Label(
            ctrl_row,
            text="[←/→ Step  |  P Play  |  Wheel Zoom  |  Drag Pan]",
            bg=THEME["panel"],
            fg=THEME["text_muted"],
            font=("Segoe UI", 8),
        ).pack(side=tk.RIGHT)

    def _bind_shortcuts(self) -> None:
        def _if_not_entry(fn):
            def handler(event):
                if isinstance(event.widget, (tk.Entry, tk.Text)):
                    return
                fn()
                return "break"
            return handler

        self.tk.bind("<Right>", _if_not_entry(self.step_next))
        self.tk.bind("<Left>", _if_not_entry(self.step_prev))
        self.tk.bind("<space>", _if_not_entry(self.step_next))
        self.tk.bind("<p>", _if_not_entry(self.toggle_play))
        self.tk.bind("<P>", _if_not_entry(self.toggle_play))
        self.tk.bind("<Home>", _if_not_entry(self.step_first))
        self.tk.bind("<End>", _if_not_entry(self.step_last))
        self.tk.bind("<plus>", _if_not_entry(lambda: self.zoom_center(1.2)))
        self.tk.bind("<equal>", _if_not_entry(lambda: self.zoom_center(1.2)))
        self.tk.bind("<minus>", _if_not_entry(lambda: self.zoom_center(1 / 1.2)))
        self.tk.bind("<0>", _if_not_entry(self.fit_to_view))

    def _initial_fit_and_render(self) -> None:
        self.fit_to_view()
        self.load_trace(self.trace, start_at=0)

    # -----------------------------------------------------------------------
    # Operation Triggers & Presets
    # -----------------------------------------------------------------------

    def _parse_x(self) -> Optional[int]:
        raw = self.x_var.get().strip()
        try:
            val = int(raw)
        except ValueError:
            messagebox.showwarning("Invalid Key", f"Please enter an integer between 0 and {self.engine.u - 1}.")
            return None
        if val < 0 or val >= self.engine.u:
            messagebox.showwarning(
                "Key Out of Range",
                f"Key x must satisfy 0 <= x < U ({self.engine.u}).\nValid range: 0 to {self.engine.u - 1}.",
            )
            return None
        return val

    def on_change_universe(self) -> None:
        self.stop_play()
        new_u = int(self.universe_var.get())
        self.engine = VEBEngine(new_u)
        self.layouts, self.bounds = compute_tree_layout(self.engine.root)
        self._selected_node_id = None
        # Clamp x_var to valid range
        try:
            cur_x = int(self.x_var.get())
        except ValueError:
            cur_x = 0
        if cur_x < 0 or cur_x >= new_u:
            self.x_var.set(str(min(new_u - 1, max(0, new_u // 2 - 1))))
        self.load_trace([self.engine.make_idle_snapshot()], start_at=0)
        self.fit_to_view()

    def on_reset(self) -> None:
        self.on_change_universe()

    def on_operation(self, op_name: str) -> None:
        self.stop_play()
        x = self._parse_x()
        if x is None:
            return

        # Make sure the engine is at the final state of the previous trace
        # (so scrubbing backward and running a new op continues from the displayed state!)
        if self.trace:
            self.engine.restore_states(self.trace[self.step_idx].node_states)

        if op_name == "insert":
            steps = self.engine.run_insert(x)
        elif op_name == "deleteVal":
            steps = self.engine.run_delete(x)
        elif op_name == "member":
            _, steps = self.engine.run_member(x)
        elif op_name == "successor":
            _, steps = self.engine.run_successor(x)
        elif op_name == "predecessor":
            _, steps = self.engine.run_predecessor(x)
        else:
            return

        self.load_trace(steps, start_at=0)
        self.start_play()

    def on_demo_guide(self) -> None:
        """Load the exact example from vEB_Tree_Guide.md: U=16, insert 2,3,7,14,15 + successor/pred/delete."""
        self.stop_play()
        self.universe_var.set("16")
        self.engine = VEBEngine(16)
        self.layouts, self.bounds = compute_tree_layout(self.engine.root)
        self._selected_node_id = None

        commands = [
            ("insert", 2),
            ("insert", 3),
            ("insert", 7),
            ("insert", 14),
            ("insert", 15),
            ("successor", 3),
            ("successor", 7),
            ("predecessor", 7),
            ("deleteVal", 7),
            ("successor", 3),
        ]
        all_steps = self._run_command_sequence(commands)
        self.load_trace(all_steps, start_at=0)
        self.fit_to_view()
        self.start_play()

    def on_random_fill(self) -> None:
        self.stop_play()
        u = self.engine.u
        self.engine = VEBEngine(u)
        self.layouts, self.bounds = compute_tree_layout(self.engine.root)
        count = max(2, min(8, u // 3))
        nums = random.sample(range(u), count)
        for n in nums:
            self.engine.run_insert(n)
        snap = self.engine.make_idle_snapshot(
            f"Populated U = {u} with random keys: {sorted(nums)}. "
            f"Try Insert, Delete, Member, Successor, or Predecessor to watch step-by-step!"
        )
        self.load_trace([snap], start_at=0)
        self.fit_to_view()

    def _run_command_sequence(self, commands: List[Tuple[str, int]]) -> List[StepSnapshot]:
        combined: List[StepSnapshot] = []
        for op, x in commands:
            if op == "insert":
                part = self.engine.run_insert(x)
            elif op == "deleteVal":
                part = self.engine.run_delete(x)
            elif op == "member":
                _, part = self.engine.run_member(x)
            elif op == "successor":
                _, part = self.engine.run_successor(x)
            elif op == "predecessor":
                _, part = self.engine.run_predecessor(x)
            else:
                continue
            for s in part:
                s.step_index = len(combined)
                combined.append(s)
        return combined

    def open_script_dialog(self) -> None:
        """Modal dialog to run a multi-instruction sequence into one continuous step trace."""
        self.stop_play()
        dlg = tk.Toplevel(self.tk)
        dlg.title("Run Instruction Script (Step-by-Step)")
        dlg.geometry("460x360")
        dlg.configure(bg=THEME["panel"])
        dlg.transient(self.tk)
        dlg.grab_set()

        tk.Label(
            dlg,
            text=f"Enter one instruction per line (valid keys: 0..{self.engine.u - 1}):",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 10, "bold"),
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=(10, 2))

        tk.Label(
            dlg,
            text="Supported: insert X | delete X | member X | successor X | predecessor X",
            bg=THEME["panel"],
            fg=THEME["text_dim"],
            font=("Consolas", 8),
            anchor="w",
        ).pack(fill=tk.X, padx=12, pady=(0, 6))

        txt = tk.Text(
            dlg,
            bg=THEME["canvas_bg"],
            fg=THEME["text"],
            insertbackground=THEME["active"],
            font=("Consolas", 10),
            relief=tk.FLAT,
            highlightbackground=THEME["border_light"],
            highlightthickness=1,
            height=11,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        u = self.engine.u
        sample = (
            f"insert {min(2, u - 1)}\n"
            f"insert {min(7, u - 1)}\n"
            f"insert {min(1, u - 1)}\n"
            f"successor {min(2, u - 1)}\n"
            f"delete {min(1, u - 1)}\n"
        )
        txt.insert("1.0", sample)

        reset_first_var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            dlg,
            text="Reset tree to empty before running script",
            variable=reset_first_var,
            bg=THEME["panel"],
            fg=THEME["text"],
            selectcolor=THEME["canvas_bg"],
            activebackground=THEME["panel"],
            activeforeground=THEME["text"],
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=12, pady=4)

        btn_row = tk.Frame(dlg, bg=THEME["panel"])
        btn_row.pack(fill=tk.X, padx=12, pady=(4, 10))

        def on_run() -> None:
            raw_lines = txt.get("1.0", tk.END).strip().splitlines()
            alias = {
                "insert": "insert",
                "ins": "insert",
                "add": "insert",
                "delete": "deleteVal",
                "deleteval": "deleteVal",
                "del": "deleteVal",
                "remove": "deleteVal",
                "member": "member",
                "has": "member",
                "find": "member",
                "successor": "successor",
                "succ": "successor",
                "predecessor": "predecessor",
                "pred": "predecessor",
            }
            cmds: List[Tuple[str, int]] = []
            for idx, line in enumerate(raw_lines, start=1):
                line = line.split("#")[0].strip()
                if not line:
                    continue
                parts = re.split(r"[\s(),]+", line)
                parts = [p for p in parts if p]
                if len(parts) != 2:
                    messagebox.showerror("Syntax Error", f"Line {idx}: expected '<op> <int>', got '{line}'", parent=dlg)
                    return
                op_key = alias.get(parts[0].lower())
                if not op_key:
                    messagebox.showerror("Unknown Operation", f"Line {idx}: unknown command '{parts[0]}'", parent=dlg)
                    return
                try:
                    val = int(parts[1])
                except ValueError:
                    messagebox.showerror("Invalid Key", f"Line {idx}: '{parts[1]}' is not an integer", parent=dlg)
                    return
                if val < 0 or val >= self.engine.u:
                    messagebox.showerror(
                        "Out of Range",
                        f"Line {idx}: key {val} is out of range 0..{self.engine.u - 1}",
                        parent=dlg,
                    )
                    return
                cmds.append((op_key, val))

            if not cmds:
                dlg.destroy()
                return

            if reset_first_var.get():
                self.engine = VEBEngine(self.engine.u)
                self.layouts, self.bounds = compute_tree_layout(self.engine.root)
            elif self.trace:
                self.engine.restore_states(self.trace[self.step_idx].node_states)

            all_steps = self._run_command_sequence(cmds)
            dlg.destroy()
            self.load_trace(all_steps, start_at=0)
            self.start_play()

        self._make_button(btn_row, "Cancel", dlg.destroy, bg=THEME["surface"]).pack(side=tk.RIGHT, padx=(6, 0))
        self._make_button(btn_row, "Record & Step Through", on_run, bg=THEME["btn_insert"]).pack(side=tk.RIGHT)

    # -----------------------------------------------------------------------
    # Trace Loading & Playback Controls
    # -----------------------------------------------------------------------

    def load_trace(self, steps: List[StepSnapshot], start_at: int = 0) -> None:
        self.trace = steps if steps else [self.engine.make_idle_snapshot()]
        self.step_idx = max(0, min(start_at, len(self.trace) - 1))

        self._suppress_slider = True
        self.step_scale.configure(from_=0, to=max(0, len(self.trace) - 1))
        self.step_scale.set(self.step_idx)
        self._suppress_slider = False

        # Populate step log listbox
        self.step_listbox.delete(0, tk.END)
        for i, s in enumerate(self.trace):
            prefix = f"[{i + 1:02d}] {s.op_label}"
            node_str = f"@{s.active_node_id}" if s.active_node_id else ""
            short_exp = s.explanation[:58] + ("..." if len(s.explanation) > 58 else "")
            self.step_listbox.insert(tk.END, f"{prefix} {node_str}: {short_exp}")

        self.render_current_step()

    def goto_step(self, idx: int) -> None:
        if not self.trace:
            return
        idx = max(0, min(idx, len(self.trace) - 1))
        self.step_idx = idx
        self._suppress_slider = True
        self.step_scale.set(idx)
        self._suppress_slider = False
        self.render_current_step()

    def on_slider_move(self, val: str) -> None:
        if self._suppress_slider:
            return
        self.stop_play()
        self.goto_step(int(float(val)))

    def on_step_list_select(self, _event) -> None:
        sel = self.step_listbox.curselection()
        if sel:
            self.stop_play()
            self.goto_step(int(sel[0]))

    def step_first(self) -> None:
        self.stop_play()
        self.goto_step(0)

    def step_prev(self) -> None:
        self.stop_play()
        self.goto_step(self.step_idx - 1)

    def step_next(self) -> None:
        if self.step_idx < len(self.trace) - 1:
            self.goto_step(self.step_idx + 1)
        else:
            self.stop_play()

    def step_last(self) -> None:
        self.stop_play()
        self.goto_step(len(self.trace) - 1)

    def toggle_play(self) -> None:
        if self.is_playing:
            self.stop_play()
        else:
            if self.step_idx >= len(self.trace) - 1:
                self.goto_step(0)
            self.start_play()

    def start_play(self) -> None:
        if len(self.trace) <= 1:
            return
        self.is_playing = True
        self.play_btn.configure(text="⏸ Pause", bg=THEME["btn_succ"])
        self._schedule_next_tick()

    def stop_play(self) -> None:
        self.is_playing = False
        if self._play_after_id is not None:
            self.tk.after_cancel(self._play_after_id)
            self._play_after_id = None
        self.play_btn.configure(text="▶ Play", bg=THEME["btn_member"])

    def _schedule_next_tick(self) -> None:
        if not self.is_playing:
            return
        if self.step_idx >= len(self.trace) - 1:
            self.stop_play()
            return
        delay = max(100, int(self.speed_var.get()))
        self._play_after_id = self.tk.after(delay, self._on_play_tick)

    def _on_play_tick(self) -> None:
        self._play_after_id = None
        if not self.is_playing:
            return
        self.step_next()
        if self.is_playing:
            self._schedule_next_tick()

    # -----------------------------------------------------------------------
    # Camera / Zoom / Pan
    # -----------------------------------------------------------------------

    def world_to_screen(self, wx: float, wy: float) -> Tuple[float, float]:
        return wx * self.zoom + self.pan_x, wy * self.zoom + self.pan_y

    def screen_to_world(self, sx: float, sy: float) -> Tuple[float, float]:
        return (sx - self.pan_x) / self.zoom, (sy - self.pan_y) / self.zoom

    def fit_to_view(self) -> None:
        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())
        min_x, min_y, max_x, max_y = self.bounds
        bw = max(1.0, max_x - min_x)
        bh = max(1.0, max_y - min_y)
        self.zoom = min(1.25, max(0.28, min((cw - 24) / bw, (ch - 24) / bh)))
        self.pan_x = (cw - bw * self.zoom) / 2.0 - min_x * self.zoom
        self.pan_y = (ch - bh * self.zoom) / 2.0 - min_y * self.zoom
        self.render_tree()

    def focus_active_node(self) -> None:
        snap = self.trace[self.step_idx]
        nid = snap.active_node_id or "root"
        if nid not in self.layouts:
            return
        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())
        nl = self.layouts[nid]
        self.zoom = max(self.zoom, 0.9)
        self.pan_x = cw / 2.0 - nl.x * self.zoom
        self.pan_y = ch / 2.0 - nl.y * self.zoom
        self.render_tree()

    def _ensure_active_visible(self, nid: str) -> None:
        if not nid or nid not in self.layouts or not self.auto_follow_var.get():
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 50 or ch < 50:
            return
        nl = self.layouts[nid]
        sx, sy = self.world_to_screen(nl.x, nl.y)
        margin_x = 90
        margin_y = 75
        if sx < margin_x or sx > cw - margin_x or sy < margin_y or sy > ch - margin_y:
            self.pan_x += (cw / 2.0 - sx) * 0.85
            self.pan_y += (ch / 2.0 - sy) * 0.85

    def _zoom_at(self, sx: float, sy: float, factor: float) -> None:
        new_zoom = min(2.4, max(0.22, self.zoom * factor))
        wx, wy = self.screen_to_world(sx, sy)
        self.zoom = new_zoom
        self.pan_x = sx - wx * self.zoom
        self.pan_y = sy - wy * self.zoom
        self.render_tree()

    def zoom_center(self, factor: float) -> None:
        cw = max(100, self.canvas.winfo_width())
        ch = max(100, self.canvas.winfo_height())
        self._zoom_at(cw / 2.0, ch / 2.0, factor)

    def on_canvas_wheel(self, event) -> None:
        factor = 1.15 if event.delta > 0 else 1 / 1.15
        self._zoom_at(event.x, event.y, factor)

    def on_canvas_press(self, event) -> None:
        self._drag_start = (event.x, event.y)
        self._drag_moved = False

    def on_canvas_drag(self, event) -> None:
        if self._drag_start is None:
            return
        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        if abs(dx) > 2 or abs(dy) > 2:
            self._drag_moved = True
        self.pan_x += dx
        self.pan_y += dy
        self._drag_start = (event.x, event.y)
        self.render_tree()

    def on_canvas_release(self, event) -> None:
        if not getattr(self, "_drag_moved", False):
            # Hit-test node click for inspection
            wx, wy = self.screen_to_world(event.x, event.y)
            clicked: Optional[str] = None
            for nid, nl in self.layouts.items():
                if abs(wx - nl.x) <= nl.w / 2 and abs(wy - nl.y) <= nl.h / 2:
                    clicked = nid
                    break
            self._selected_node_id = clicked
            if clicked:
                node = self.engine.node_map[clicked]
                snap = self.trace[self.step_idx]
                mn, mx = snap.node_states.get(clicked, (None, None))
                kind = "Summary subtree" if node.is_summary else ("Root" if clicked == "root" else "Cluster subtree")
                self.node_inspect_label.configure(
                    text=f"Selected: {clicked} ({kind}, U={node.u}, {node.range_label}) | min={fmt_val(mn)}, max={fmt_val(mx)}",
                    fg=THEME["active"],
                )
            else:
                self.node_inspect_label.configure(
                    text="Tip: click any universe cell to fill Key x, or click any tree node to inspect it",
                    fg=THEME["text_muted"],
                )
            self.render_tree()
        self._drag_start = None

    def on_strip_click(self, event) -> None:
        """Clicking a slot in the universe strip populates Key x for convenience."""
        u = self.engine.u
        w = max(200, self.strip_canvas.winfo_width())
        pad = 10
        cell_w = (w - 2 * pad) / u
        idx = int((event.x - pad) // cell_w)
        if 0 <= idx < u:
            self.x_var.set(str(idx))

    # -----------------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------------

    def render_current_step(self) -> None:
        snap = self.trace[self.step_idx]
        self._ensure_active_visible(snap.active_node_id)

        # Header badges
        self.op_badge_lbl.configure(text=snap.op_label.upper())
        self.step_counter_lbl.configure(text=f"Step {self.step_idx + 1} / {len(self.trace)}")

        if snap.result_val:
            col = THEME["not_found"] if ("NIL" in snap.result_val or "False" in snap.result_val or "not found" in snap.result_val) else THEME["found"]
            self.result_badge_label.configure(text=f"Result: {snap.result_val}", fg=col)
        else:
            self.result_badge_label.configure(text="")

        # Explanation text
        self.explanation_text.configure(state=tk.NORMAL)
        self.explanation_text.delete("1.0", tk.END)
        self.explanation_text.insert("1.0", snap.explanation)
        self.explanation_text.configure(state=tk.DISABLED)

        # Live Code Viewer
        self.render_code_panel(snap)

        # Local Variables chips
        for child in self.vars_frame.winfo_children():
            child.destroy()
        row_frame = tk.Frame(self.vars_frame, bg=THEME["panel_alt"])
        row_frame.pack(side=tk.TOP, fill=tk.X)
        col_count = 0
        for k, v in snap.variables.items():
            if col_count >= 3:
                row_frame = tk.Frame(self.vars_frame, bg=THEME["panel_alt"])
                row_frame.pack(side=tk.TOP, fill=tk.X, pady=(3, 0))
                col_count = 0
            chip = tk.Frame(row_frame, bg=THEME["surface"], highlightbackground=THEME["border"], highlightthickness=1)
            chip.pack(side=tk.LEFT, padx=(0, 5))
            tk.Label(chip, text=f"{k}:", bg=THEME["surface"], fg=THEME["text_dim"], font=("Consolas", 8)).pack(
                side=tk.LEFT, padx=(5, 2), pady=2
            )
            tk.Label(chip, text=v, bg=THEME["surface"], fg=THEME["active"], font=("Consolas", 8, "bold")).pack(
                side=tk.LEFT, padx=(0, 5), pady=2
            )
            col_count += 1

        # Call Stack
        self.stack_listbox.delete(0, tk.END)
        if snap.call_stack:
            for depth, frame in enumerate(snap.call_stack):
                indent = "  " * depth
                marker = "▶ " if depth == len(snap.call_stack) - 1 else "│ "
                self.stack_listbox.insert(tk.END, f"{indent}{marker}{frame}")
            last = len(snap.call_stack) - 1
            self.stack_listbox.itemconfig(last, fg=THEME["active"])
            self.stack_listbox.see(last)
        else:
            self.stack_listbox.insert(tk.END, "(call stack empty)")
            self.stack_listbox.itemconfig(0, fg=THEME["text_muted"])

        # Highlight current step in step log
        self.step_listbox.selection_clear(0, tk.END)
        if 0 <= self.step_idx < self.step_listbox.size():
            self.step_listbox.selection_set(self.step_idx)
            self.step_listbox.see(self.step_idx)

        self.render_universe_strip()
        self.render_tree()

    def render_code_panel(self, snap: StepSnapshot) -> None:
        lines = CODE_LISTINGS.get(snap.op_name, CODE_LISTINGS["insert"])
        self.code_title_lbl.configure(text=f"C Algorithm — {snap.op_name}()  [vanEmdeBoasTrees.h]")
        self.code_text.configure(state=tk.NORMAL)
        self.code_text.delete("1.0", tk.END)
        for lineno, text in enumerate(lines, start=1):
            is_active = lineno == snap.active_line
            prefix = "▶ " if is_active else "  "
            self.code_text.insert(tk.END, prefix, "arrow" if is_active else ())
            self.code_text.insert(tk.END, f"{lineno:2d} ", "active_line" if is_active else "lineno")
            self.code_text.insert(tk.END, text + "\n", "active_line" if is_active else ())
        if snap.active_line > 0:
            self.code_text.see(f"{snap.active_line}.0")
        self.code_text.configure(state=tk.DISABLED)

    def render_universe_strip(self) -> None:
        c = self.strip_canvas
        c.delete("all")
        snap = self.trace[self.step_idx]
        u = self.engine.u
        elems = snap.elements
        root_min, root_max = snap.node_states.get("root", (None, None))

        sorted_elems = sorted(elems)
        preview = ", ".join(map(str, sorted_elems[:16])) + (" ..." if len(sorted_elems) > 16 else "")
        self.strip_info_label.configure(
            text=f"Universe [0..{u - 1}]  |  Stored ({len(elems)}): {{ {preview} }}  |  min={fmt_val(root_min)}, max={fmt_val(root_max)}"
        )

        w = max(240, c.winfo_width())
        h = max(40, c.winfo_height())
        pad = 10
        cell_w = (w - 2 * pad) / u
        cluster_sz = lower_sqrt(u) if u > 2 else 2

        # Draw cluster grouping brackets at top
        if u > 2:
            num_clusters = upper_sqrt(u)
            for ci in range(num_clusters):
                x0 = pad + ci * cluster_sz * cell_w + 1
                x1 = pad + (ci + 1) * cluster_sz * cell_w - 1
                c.create_line(x0, 9, x1, 9, fill=THEME["border_light"], width=1)
                if (x1 - x0) >= 24:
                    c.create_text(
                        (x0 + x1) / 2,
                        5,
                        text=f"C{ci}",
                        fill=THEME["text_muted"],
                        font=("Consolas", 7),
                    )

        # Draw cells
        font_sz = 9 if cell_w >= 22 else (8 if cell_w >= 14 else 6)
        for i in range(u):
            x0 = pad + i * cell_w + 1
            x1 = pad + (i + 1) * cell_w - 1
            y0, y1 = 13, h - 5

            in_set = i in elems
            is_query = snap.query_x == i
            is_in_flight = snap.in_flight_x == i and not in_set

            fill = "#166534" if in_set else THEME["canvas_bg"]
            outline = THEME["found"] if in_set else THEME["border"]
            width = 1
            txt_col = "#ffffff" if in_set else THEME["text_muted"]

            if is_in_flight:
                fill = "#831843"
                outline = THEME["swap"]
                width = 2
                txt_col = "#ffffff"
            if is_query:
                outline = THEME["active"]
                width = 2

            c.create_rectangle(x0, y0, x1, y1, fill=fill, outline=outline, width=width)
            if cell_w >= 11:
                c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=str(i), fill=txt_col, font=("Consolas", font_sz, "bold" if in_set else "normal"))

    def render_tree(self) -> None:
        c = self.canvas
        c.delete("all")
        snap = self.trace[self.step_idx]
        stack_edge_set = set(snap.stack_edges)

        # 1. Draw all edges first
        for nid, node in self.engine.node_map.items():
            if node.u <= 2:
                continue
            p_lay = self.layouts[nid]
            px, py = self.world_to_screen(p_lay.x, p_lay.y + p_lay.h / 2)

            children: List[Tuple[VEBNode, str, bool]] = []
            if node.summary is not None:
                children.append((node.summary, "S", True))
            for idx, ch in enumerate(node.clusters):
                children.append((ch, f"C{idx}", False))

            for ch, edge_lbl, is_sum_edge in children:
                c_lay = self.layouts[ch.node_id]
                cx, cy = self.world_to_screen(c_lay.x, c_lay.y - c_lay.h / 2)
                edge_key = (nid, ch.node_id)

                is_active_edge = snap.active_edge == edge_key
                is_stack_edge = edge_key in stack_edge_set

                if is_active_edge:
                    color = THEME["active"]
                    width = max(2.5, 3.0 * self.zoom)
                    dash = ()
                elif is_stack_edge:
                    color = THEME["stack"]
                    width = max(2.0, 2.4 * self.zoom)
                    dash = ()
                elif is_sum_edge:
                    color = THEME["summary_edge"]
                    width = max(1.0, 1.4 * self.zoom)
                    dash = (4, 3)
                else:
                    color = THEME["cluster_edge"]
                    width = max(1.0, 1.3 * self.zoom)
                    dash = ()

                mid_y = (py + cy) / 2.0
                c.create_line(
                    px, py, px, mid_y, cx, mid_y, cx, cy,
                    fill=color,
                    width=width,
                    dash=dash,
                    smooth=False,
                    arrow=tk.LAST if is_active_edge else tk.NONE,
                    arrowshape=(8, 10, 4),
                )

                # Edge label when zoomed enough
                if self.zoom >= 0.55:
                    lx = cx
                    ly = cy - 9 * self.zoom
                    lbl_col = color if (is_active_edge or is_stack_edge or is_sum_edge) else THEME["text_muted"]
                    c.create_text(
                        lx,
                        ly,
                        text=edge_lbl,
                        fill=lbl_col,
                        font=("Consolas", max(7, int(8 * self.zoom)), "bold" if is_active_edge else "normal"),
                    )

        # 2. Draw all nodes
        for nid, node in self.engine.node_map.items():
            nl = self.layouts[nid]
            mn, mx = snap.node_states.get(nid, (None, None))
            role = snap.node_roles.get(nid)
            f_hl = snap.field_highlights.get(nid, set())
            self._draw_node(node, nl, mn, mx, role, f_hl, snap)

    def _draw_node(
        self,
        node: VEBNode,
        nl: NodeLayout,
        mn: Optional[int],
        mx: Optional[int],
        role: Optional[str],
        field_hl: Set[str],
        snap: StepSnapshot,
    ) -> None:
        c = self.canvas
        x0, y0 = self.world_to_screen(nl.x - nl.w / 2, nl.y - nl.h / 2)
        x1, y1 = self.world_to_screen(nl.x + nl.w / 2, nl.y + nl.h / 2)
        sw = x1 - x0
        sh = y1 - y0
        if sw < 14 or sh < 10:
            return

        is_empty = mn is None
        is_selected = self._selected_node_id == node.node_id

        # Colors based on role and node type
        if role in THEME:
            border_col = THEME[role]
            border_w = max(2, int(3 * self.zoom)) if role != "stack" else max(2, int(2.2 * self.zoom))
        elif is_selected:
            border_col = "#ffffff"
            border_w = 2
        elif node.is_summary:
            border_col = THEME["summary_border"] if not is_empty else "#4c1d95"
            border_w = 1.5 if not is_empty else 1
        else:
            border_col = THEME["cluster_border"] if not is_empty else THEME["border"]
            border_w = 1.5 if not is_empty else 1

        body_bg = THEME["empty_bg"] if is_empty else THEME["occupied_bg"]
        if node.node_id == "root":
            hdr_bg = THEME["root_hdr"]
        elif node.is_summary:
            hdr_bg = THEME["summary_hdr"] if not is_empty else "#2e1065"
        else:
            hdr_bg = THEME["cluster_hdr"] if not is_empty else "#172033"

        # Glow halo for active / swap / updated / found node
        if role in ("active", "swap", "updated", "found", "not_found"):
            pad = max(3, int(4 * self.zoom))
            c.create_rectangle(
                x0 - pad, y0 - pad, x1 + pad, y1 + pad,
                fill="",
                outline=border_col,
                width=1,
                dash=(3, 2),
            )

        # Card body
        c.create_rectangle(x0, y0, x1, y1, fill=body_bg, outline=border_col, width=border_w)

        # Header band
        hdr_h = sh * 0.36
        c.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y0 + hdr_h, fill=hdr_bg, outline="")

        hdr_font_sz = max(6, int(8.5 * self.zoom))
        if sw >= 38:
            c.create_text(
                x0 + 5 * self.zoom,
                y0 + hdr_h / 2,
                text=node.label,
                anchor="w",
                fill=THEME["text"] if not is_empty or role else THEME["text_dim"],
                font=("Consolas", hdr_font_sz, "bold"),
            )
            c.create_text(
                x1 - 5 * self.zoom,
                y0 + hdr_h / 2,
                text=f"U={node.u}",
                anchor="e",
                fill=THEME["text_dim"],
                font=("Consolas", max(6, int(7.5 * self.zoom))),
            )

        # Range subtitle for internal nodes when zoomed enough
        body_top = y0 + hdr_h
        if node.u > 2 and self.zoom >= 0.65:
            sub_h = sh * 0.19
            c.create_text(
                (x0 + x1) / 2,
                body_top + sub_h / 2,
                text=node.range_label,
                fill=THEME["text_muted"],
                font=("Consolas", max(6, int(7 * self.zoom))),
            )
            cells_top = body_top + sub_h + 2 * self.zoom
        else:
            cells_top = body_top + 3 * self.zoom

        # Min / Max cells
        cell_pad = max(2, int(4 * self.zoom))
        mid_x = (x0 + x1) / 2
        cells_bot = y1 - cell_pad

        for field_name, val, cx0, cx1 in [
            ("min", mn, x0 + cell_pad, mid_x - cell_pad / 2),
            ("max", mx, mid_x + cell_pad / 2, x1 - cell_pad),
        ]:
            hl = field_name in field_hl
            c_fill = "#1e3a5f" if hl else (THEME["surface"] if val is not None else "#0d1424")
            if hl and role in ("updated", "swap", "found"):
                c_outline = THEME[role]
            elif hl:
                c_outline = THEME["checked"]
            else:
                c_outline = THEME["border_light"] if val is not None else THEME["border"]

            c.create_rectangle(cx0, cells_top, cx1, cells_bot, fill=c_fill, outline=c_outline, width=2 if hl else 1)

            val_str = "—" if val is None else str(val)
            txt_col = "#ffffff" if (val is not None or hl) else THEME["text_muted"]
            val_font_sz = max(6, int(8.5 * self.zoom))
            if (cx1 - cx0) >= 24:
                lbl_text = f"{field_name[0]}:{val_str}" if (cx1 - cx0) < 42 else f"{field_name}:{val_str}"
                c.create_text(
                    (cx0 + cx1) / 2,
                    (cells_top + cells_bot) / 2,
                    text=lbl_text,
                    fill=txt_col,
                    font=("Consolas", val_font_sz, "bold" if (val is not None or hl) else "normal"),
                )

        # Floating badge above active node
        if node.node_id == snap.active_node_id and snap.node_badge and self.zoom >= 0.45:
            badge_col = THEME.get(role or "active", THEME["active"])
            bf_sz = max(7, int(8.5 * self.zoom))
            bx = (x0 + x1) / 2
            by = y0 - max(12, int(14 * self.zoom))
            bw = max(len(snap.node_badge) * bf_sz * 0.68 + 12, 46)
            bh = max(14, int(17 * self.zoom))
            c.create_rectangle(
                bx - bw / 2, by - bh / 2, bx + bw / 2, by + bh / 2,
                fill=badge_col,
                outline="#ffffff",
                width=1,
            )
            c.create_text(
                bx, by,
                text=snap.node_badge,
                fill="#0b1120",
                font=("Consolas", bf_sz, "bold"),
            )


def main() -> None:
    root = tk.Tk()
    VEBVisualizerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
