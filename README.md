# DS Helper Series

A growing collection of ready-to-use Data Structure header files in C, paired with simple guides so you can understand how they work and plug them straight into your own code.

Pick a structure from the list below, drop the `.h` file into your project, and try it out.

## Data Structures in This Series

| Data Structure | Language | Header File | Guide |
| :--- | :--- | :--- | :--- |
| van Emde Boas (vEB) Tree | C | [vanEmdeBoasTrees.h](./van%20Emde%20Boas%20Tree/vanEmdeBoasTrees.h) | [vEB_Tree_Guide.md](./van%20Emde%20Boas%20Tree/vEB_Tree_Guide.md) |

More data structures are on the way. Watch or star the repo if you want to follow along as new ones get added.

## How to Use a File

1. Download the `.h` file from any folder (or clone this repo).
2. Include it at the top of your C file.
3. Compile and run.

### Quick Example (van Emde Boas Tree)

Create a `main.c` file in the same folder as `vanEmdeBoasTrees.h`:

```c
#include "vanEmdeBoasTrees.h"

int main() {
    vEB* tree = create(16); // Stores numbers from 0 to 15

    insert(tree, 2);
    insert(tree, 7);
    insert(tree, 14);

    printf("Has 7? %s\n", member(tree, 7) ? "Yes" : "No");
    printf("Next after 2: %d\n", successor(tree, 2));

    freeTree(tree);
    return 0;
}
```

Compile with GCC (add `-lm` to link the math library):

```bash
gcc main.c -lm -o demo
./demo
```

On Windows PowerShell, run `.\demo.exe` instead of `./demo`.

## Folder Layout

Each data structure lives in its own folder with two files:

```text
DS Helper Series/
└── van Emde Boas Tree/
    ├── vanEmdeBoasTrees.h   # Ready-to-include C implementation
    └── vEB_Tree_Guide.md    # Beginner guide with examples and rules
```

## Request a Data Structure or Share Feedback

Learning something new and want to see a specific data structure added next?

- **Request a topic:** Open an issue and name the data structure you want to see.
- **Found a bug?** Open an issue or send a pull request with a fix.
- **Questions about the code?** Check the guide inside each folder first, or open an issue and ask.
