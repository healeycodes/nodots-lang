# data structures (implementation as native functions)

```
d = list(1, 2, 3, 4);
set(d, 0, -1); # mutate 0th item
at(d, 0); # get 0th item

e = dict(
  "a", 0,
  "b", 1
);
set(e, "a", -1); mutate by key
at(e, "a"); get by key
at(e, "z"); nil (missing)

keys(e); # maybe?
values(e); # maybe?
```

# maybe some functional stuff?

```
map(list(1, 2), fun _(i) return i * i; nuf);
foreach(list(1, 2), fun _(i) log(i); nuf);
filter(list(true, false), fun(x) return x; nuf);
```

# traditional for loops?
```
for (i = 0; i < 5; i = i + 1)
  log(i);
rof
```
