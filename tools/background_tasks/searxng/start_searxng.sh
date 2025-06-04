docker run --rm -d \
    -p 8080:8080 \
    -v "${PWD}/tools/background_tasks/searxng:/etc/searxng" \
    -e "BASE_URL=http://localhost:8080/" \
    -e "INSTANCE_NAME=searxng" \
    searxng/searxng:latest