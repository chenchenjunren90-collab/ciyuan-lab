#include <stdio.h>

int main(void) {
    int year;
    if (scanf("%d", &year) != 1) return 1;
    int leap = year % 400 == 0 || (year % 4 == 0 && year % 100 != 0);
    printf("%d\n", leap);
    return 0;
}
