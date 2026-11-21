#include <stdio.h>
#include <stdlib.h>
#include <math.h>

#define NIL -1

typedef struct vanEmdeBoasTree {
    int universeSize;
    int min;
    int max;
    struct vanEmdeBoasTree* summary;
    struct vanEmdeBoasTree** clusters;
} vEB;

// Helper functions to compute upper and lower square roots
int upperSqrt(int u) {
    return (int)pow(2, ceil(log2(u) / 2.0));
}

int lowerSqrt(int u) {
    return (int)pow(2, floor(log2(u) / 2.0));
}

// Helper functions to navigate the tree
int high(vEB* tree, int x) {
    return x / lowerSqrt(tree->universeSize);
}

int low(vEB* tree, int x) {
    return x % lowerSqrt(tree->universeSize);
}

int indexOf(vEB* tree, int x, int y) {
    return x * lowerSqrt(tree->universeSize) + y;
}

// Create and initialize a vEB tree of size U (U should be a power of 2)
vEB* create(int universeSize) {
    vEB* tree = (vEB*)malloc(sizeof(vEB));
    tree->universeSize = universeSize;
    tree->min = NIL;
    tree->max = NIL;

    if (universeSize <= 2) {
        tree->summary = NULL;
        tree->clusters = NULL;
    } else {
        int upper = upperSqrt(universeSize);
        int lower = lowerSqrt(universeSize);

        tree->summary = create(upper);
        tree->clusters = (vEB**)malloc(upper * sizeof(vEB*));
        for (int i = 0; i < upper; i++) {
            tree->clusters[i] = create(lower);
        }
    }
    return tree;
}

// Check if an element x exists in the tree - O(log log U)
int member(vEB* tree, int x) {
    if (x == tree->min || x == tree->max) {
        return 1;
    }
    if (tree->universeSize <= 2) {
        return 0;
    }
    return member(tree->clusters[high(tree, x)], low(tree, x));
}

// Helper for inserting into an empty tree - O(1)
void emptyInsert(vEB* tree, int x) {
    tree->min = x;
    tree->max = x;
}

// Insert an element x into the tree - O(log log U)
void insert(vEB* tree, int x) {
    if (tree->min == NIL) {
        emptyInsert(tree, x);
        return;
    }

    if (x < tree->min) {
        // Swap x and tree->min so the smaller element stays at the top
        int temp = x;
        x = tree->min;
        tree->min = temp;
    }

    if (tree->universeSize > 2) {
        int h = high(tree, x);
        int l = low(tree, x);

        if (tree->clusters[h]->min == NIL) {
            insert(tree->summary, h);
            emptyInsert(tree->clusters[h], l);
        } else {
            insert(tree->clusters[h], l);
        }
    }

    if (x > tree->max) {
        tree->max = x;
    }
}

// Find the smallest element strictly greater than x - O(log log U)
int successor(vEB* tree, int x) {
    if (tree->universeSize <= 2) {
        if (x == 0 && tree->max == 1) return 1;
        return NIL;
    }
    if (tree->min != NIL && x < tree->min) {
        return tree->min;
    }

    int h = high(tree, x);
    int l = low(tree, x);
    int maxLow = tree->clusters[h]->max;

    // If successor is in the same cluster
    if (maxLow != NIL && l < maxLow) {
        int offset = successor(tree->clusters[h], l);
        return indexOf(tree, h, offset);
    } else {
        // Look for the next non-empty cluster via summary
        int succCluster = successor(tree->summary, h);
        if (succCluster == NIL) {
            return NIL;
        }
        int offset = tree->clusters[succCluster]->min;
        return indexOf(tree, succCluster, offset);
    }
}

// Find the largest element strictly less than x - O(log log U)
int predecessor(vEB* tree, int x) {
    if (tree->universeSize <= 2) {
        if (x == 1 && tree->min == 0) return 0;
        return NIL;
    }
    if (tree->max != NIL && x > tree->max) {
        return tree->max;
    }

    int h = high(tree, x);
    int l = low(tree, x);
    int minLow = tree->clusters[h]->min;

    // If predecessor is in the same cluster
    if (minLow != NIL && l > minLow) {
        int offset = predecessor(tree->clusters[h], l);
        return indexOf(tree, h, offset);
    } else {
        // Look for the previous non-empty cluster via summary
        int predCluster = predecessor(tree->summary, h);
        if (predCluster == NIL) {
            // Check if tree->min is the predecessor (since min isn't stored in clusters)
            if (tree->min != NIL && x > tree->min) {
                return tree->min;
            }
            return NIL;
        }
        int offset = tree->clusters[predCluster]->max;
        return indexOf(tree, predCluster, offset);
    }
}

// Delete an element x from the tree - O(log log U)
void deleteVal(vEB* tree, int x) {
    if (tree->min == tree->max) {
        tree->min = NIL;
        tree->max = NIL;
        return;
    }

    if (tree->universeSize <= 2) {
        if (x == 0) tree->min = 1;
        else tree->min = 0;
        tree->max = tree->min;
        return;
    }

    // If deleting min, replace min with the smallest element in the clusters
    if (x == tree->min) {
        int firstCluster = tree->summary->min;
        x = indexOf(tree, firstCluster, tree->clusters[firstCluster]->min);
        tree->min = x;
    }

    int h = high(tree, x);
    int l = low(tree, x);
    deleteVal(tree->clusters[h], l);

    // If the cluster became empty, update summary and max
    if (tree->clusters[h]->min == NIL) {
        deleteVal(tree->summary, h);
        if (x == tree->max) {
            int summaryMax = tree->summary->max;
            if (summaryMax == NIL) {
                tree->max = tree->min;
            } else {
                tree->max = indexOf(tree, summaryMax, tree->clusters[summaryMax]->max);
            }
        }
    } else if (x == tree->max) {
        tree->max = indexOf(tree, h, tree->clusters[h]->max);
    }
}

// Free allocated memory
void freeTree(vEB* tree) {
    if (!tree) return;
    if (tree->universeSize > 2) {
        int upper = upperSqrt(tree->universeSize);
        freeTree(tree->summary);
        for (int i = 0; i < upper; i++) {
            freeTree(tree->clusters[i]);
        }
        free(tree->clusters);
    }
    free(tree);
}