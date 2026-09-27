#include <stdio.h>
#include <string.h>

int main(void) {
    char text[102];
    if (fgets(text, sizeof text, stdin) == NULL) return 1;
    size_t length = strcspn(text, "\n");
    for (size_t i = length; i > 0; --i) putchar(text[i - 1]);
    putchar('\n');
    return 0;
}
