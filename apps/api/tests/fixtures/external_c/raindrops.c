#include <stdio.h>

int main(void) {
    int number, matched = 0;
    if (scanf("%d", &number) != 1) return 1;
    if (number % 3 == 0) { printf("Pling"); matched = 1; }
    if (number % 5 == 0) { printf("Plang"); matched = 1; }
    if (number % 7 == 0) { printf("Plong"); matched = 1; }
    if (!matched) printf("%d", number);
    putchar('\n');
    return 0;
}
