docker run -d \
  -p 11235:11235 \
  --name crawl4ai \
  --rm \
  --shm-size=32g \
  unclecode/crawl4ai:0.6.0-r1
