# Sims2 Reia File Library

This is a parser for Sims 2 `.reia` files in Python.

## Basic Usage

Read a `.reia` file:

```python
with open("N001.reia", "rb") as f:
    reia_file = sims_reia.read_from_file(f)
    print(f"resolution={reia_file.width}x{reia_file.height}, fps={reia_file.frames_per_second}")

    for i, frame in enumerate(reia_file.frames):
        frame.image.save(f"frame{i}.png")
```

## Testing

`poetry run pytest`

## Formatting

`poetry run black .`

