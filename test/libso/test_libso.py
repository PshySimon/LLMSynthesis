from utils.libs.libso import libso


@libso("./libadd.so->add")
def add(a: int, b: int) -> int: ...


print(add(2, 4))