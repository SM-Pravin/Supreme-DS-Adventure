# van Emde Boas (vEB) Tree — Simple Beginner's Guide

Welcome! If you've never heard of a **van Emde Boas (vEB) Tree**, don't worry. This guide explains what it is, why it's special, and how to use the C implementation—in plain, everyday English.

---

## 1. What Is a van Emde Boas (vEB) Tree?

A **van Emde Boas (vEB) Tree** is a super-fast way to store a set of **non-negative integers** within a fixed range (from `0` to `U - 1`) and quickly answer questions like:

- *"Is the number `7` in my set?"* (`member`)
- *"What is the next bigger number after `7`?"* (`successor`)
- *"What is the next smaller number before `7`?"* (`predecessor`)
- *"Add `12` to the set"* (`insert`) or *"Remove `7` from the set"* (`deleteVal`)

### The Everyday Analogy: A Hotel with a Directory

Imagine a hotel with **16 rooms** numbered `0` to `15`:
- Instead of walking past all 16 rooms one by one to find the next occupied room, the hotel is organized into **4 floors**, each with **4 rooms**.
- At the front desk, there is a **Summary Board** (a quick checklist of the 4 floors) that tells you which floors have *at least one guest*.
- Every floor also has a sign on its door showing the **smallest (`min`)** and **largest (`max`)** occupied room number on that floor.
- The whole hotel also has a sign at the lobby showing the overall smallest (`min`) and largest (`max`) occupied room.

Now, if you are in room `5` (Floor 1, Room 1) and want to find the **next occupied room**:
1. Check if there's a higher occupied room on Floor 1.
2. If not, check the front desk **Summary Board** to jump straight to the next non-empty floor (say, Floor 3).
3. Look at Floor 3's door sign to immediately get its smallest (`min`) occupied room!

And if the hotel had **1,000,000 rooms**, you'd split it into 1,000 wings of 1,000 rooms—and each wing would split itself the exact same way! Because the problem shrinks by a **square root** at every step instead of just half, searching becomes extraordinarily fast.

---

## 2. Why Is It So Fast?

Most data structures cut the search space in **half** at each step (like binary search or balanced binary trees). A vEB tree takes the **square root** of the search space at each step!

| Data Structure | Typical Speed | Steps for Range `U = 4,000,000,000` (4 Billion) |
| :--- | :--- | :--- |
| Unsorted Array / List | $O(N)$ | Up to 4,000,000,000 steps |
| Balanced Binary Search Tree (AVL / Red-Black) | $O(\log N)$ | ~32 steps |
| **van Emde Boas (vEB) Tree** | **$O(\log \log U)$** | **Only ~5 steps!** |

> **In simple terms:** Even if your numbers range from `0` to `4 billion`, a vEB tree finds, inserts, or deletes a number in roughly **5 tiny jumps**.

---

## 3. How the Code Organizes Numbers (Visual Breakdown)

Suppose your universe size is `U = 16` (meaning valid numbers are `0` through `15`).

The tree splits `16` into `√16 = 4` **clusters**, each holding `4` numbers:

```text
Universe Size U = 16  (Numbers 0 to 15)
├── min, max   (Overall smallest & largest numbers in the tree)
├── summary    (Mini vEB tree of size 4: tracks which clusters are NOT empty)
└── clusters:
    ├── Cluster 0  --> handles numbers  0,  1,  2,  3
    ├── Cluster 1  --> handles numbers  4,  5,  6,  7
    ├── Cluster 2  --> handles numbers  8,  9, 10, 11
    └── Cluster 3  --> handles numbers 12, 13, 14, 15
```

### How a Number Finds Its Spot (`high`, `low`, `indexOf`)

Take the number **`11`** in a tree of size `16` (where each cluster has size `4`):
- **`high(tree, 11)`** = `11 / 4 = 2` → It belongs in **Cluster 2**.
- **`low(tree, 11)`** = `11 % 4 = 3` → Inside Cluster 2, it sits at **position 3**.
- **`indexOf(tree, 2, 3)`** = `2 * 4 + 3 = 11` → Rebuilds the original number `11` from its cluster and position.

> **Clever Trick in This Code:** The overall `min` value is stored *only* in `tree->min` and **not** duplicated inside `clusters`. That tiny trick lets `insert` and `deleteVal` avoid doing two recursive calls, which is what guarantees the ultra-fast $O(\log \log U)$ speed!

---

## 4. Functions Cheat Sheet

Here is every public function you need to call:

| Function | What It Does | Return Value |
| :--- | :--- | :--- |
| `create(universeSize)` | Creates an empty vEB tree for numbers `0` to `universeSize - 1`. | Pointer to the new `vEB*` tree |
| `insert(tree, x)` | Adds integer `x` into the tree. | `void` (nothing) |
| `member(tree, x)` | Checks if `x` is currently stored in the tree. | `1` (yes) or `0` (no) |
| `successor(tree, x)` | Finds the smallest number **strictly greater** than `x`. | The number, or `NIL` (`-1`) if none exists |
| `predecessor(tree, x)` | Finds the largest number **strictly smaller** than `x`. | The number, or `NIL` (`-1`) if none exists |
| `deleteVal(tree, x)` | Removes integer `x` from the tree. | `void` (nothing) |
| `freeTree(tree)` | Frees all memory used by the tree when you're done. | `void` (nothing) |

*(Note: `NIL` is defined as `-1` and means "empty" or "not found". Functions like `upperSqrt`, `lowerSqrt`, `high`, `low`, `indexOf`, and `emptyInsert` are internal helpers—you don't need to call them directly.)*

---

## 5. How to Use It (Step-by-Step Example)

### Step 1: Put the vEB Code and a `main()` Function in a File

Save the vEB tree code in a file named `veb.c`, and add this `main()` function at the bottom:

```c
int main() {
    // 1. Create a tree that can store numbers from 0 to 15 (16 is a power of 2)
    vEB* tree = create(16);

    // 2. Insert some numbers
    int numbers[] = {2, 3, 7, 14, 15};
    int count = 5;
    for (int i = 0; i < count; i++) {
        if (!member(tree, numbers[i])) {  // Safe practice: avoid duplicates
            insert(tree, numbers[i]);
        }
    }

    // 3. Check if numbers exist in the tree
    printf("Is 7 in the tree?  %s\n", member(tree, 7) ? "Yes" : "No");
    printf("Is 10 in the tree? %s\n", member(tree, 10) ? "Yes" : "No");

    // 4. Find the next bigger (successor) and next smaller (predecessor) numbers
    printf("Next number after 3:  %d\n", successor(tree, 3));    // 7
    printf("Next number after 7:  %d\n", successor(tree, 7));    // 14
    printf("Prev number before 7: %d\n", predecessor(tree, 7));  // 3
    printf("Next number after 15: %d\n", successor(tree, 15));   // -1 (NIL)

    // 5. Delete a number (check it exists first!)
    if (member(tree, 7)) {
        deleteVal(tree, 7);
    }
    printf("After deleting 7, next number after 3: %d\n", successor(tree, 3)); // 14

    // 6. Clean up memory
    freeTree(tree);
    return 0;
}
```

### Step 2: Compile and Run

Because the code uses `pow`, `log2`, `ceil`, and `floor` from `<math.h>`, link the math library with `-lm` when compiling with `gcc`:

```bash
gcc veb.c -lm -o veb_demo
./veb_demo
```

*(On Windows with MinGW/PowerShell, run `.\veb_demo.exe`.)*

### Expected Output

```text
Is 7 in the tree?  Yes
Is 10 in the tree? No
Next number after 3:  7
Next number after 7:  14
Prev number before 7: 3
Next number after 15: -1
After deleting 7, next number after 3: 14
```

---

## 6. Important Rules & Common Pitfalls

Before using this implementation in your own program, keep these 5 rules in mind:

1. **`universeSize` must be a power of 2**
   Use sizes like `2`, `4`, `8`, `16`, `32`, `64`, `256`, `1024`, `65536`. If you need numbers up to `100`, pick the next power of 2 (`128`).
2. **Keep numbers inside `0` to `universeSize - 1`**
   Negative numbers or numbers `>= universeSize` will crash the program (out-of-bounds array access).
3. **Avoid duplicate inserts & deleting missing numbers**
   This implementation treats the tree as a mathematical **set** (unique values only):
   - Check `if (!member(tree, x))` before calling `insert(tree, x)`.
   - Check `if (member(tree, x))` before calling `deleteVal(tree, x)`.
4. **Watch your memory usage**
   `create(U)` builds the entire tree structure upfront in memory, using $O(U)$ space.
   - Great for `U` up to a few hundred thousand (e.g., `65536` or `262144`).
   - **Don't** call `create(1000000000)`—allocating a billion-sized tree upfront will run out of RAM!
5. **Always free the tree**
   Call `freeTree(tree)` when you're done so your program doesn't leak memory.

---

## 7. When Should You Use a vEB Tree?

**Great fit when:**
- You store **non-negative integers** in a known, fixed range (like port numbers `0–65535`, timestamps, task IDs, or grid indices).
- You frequently need **next/previous** queries (`successor` / `predecessor`) and want the fastest possible lookup speed.

**Not a great fit when:**
- You want to store strings, floating-point decimals, or arbitrary negative/huge 64-bit numbers (use a hash table or balanced binary search tree instead).
- Your number range `U` is massive (billions) while you only store a few items—a standard vEB tree wastes too much memory unless modified with hash tables.
