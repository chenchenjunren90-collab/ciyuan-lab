#include <stdio.h>
#include <string.h>

int main(void) {
    char first[102], second[102];
    if (fgets(first, sizeof first, stdin) == NULL ||
        fgets(second, sizeof second, stdin) == NULL) return 1;
    size_t n = strcspn(first, "\n");
    size_t m = strcspn(second, "\n");
    if (n != m) { puts("-1"); return 0; }
    int differences = 0;
    for (size_t i = 0; i < n; ++i) differences += first[i] != second[i];
    printf("%d\n", differences);
    return 0;
}
