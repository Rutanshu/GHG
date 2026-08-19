# assets/

Drop a generated hero image here as `hero-esg.jpg` (or `.png`/`.webp` — just
update the filename referenced in `index.html`'s `.bg-canvas::after` rule to
match). It's used as a very subtle, low-opacity (16%) multiply-blended layer
under the glass panels — it should read fine as a small thumbnail and still
work when almost invisible behind text, since that's how it'll actually be
seen. If the file isn't present, the page falls back cleanly to the CSS
gradient background alone; nothing breaks.

See the image-generation prompt in the project notes / README for what to
generate.
