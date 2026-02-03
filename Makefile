
all: run

SERVER_BIN = siview-server-linux-amd64
SERVER_SRC = server/main.go

$(SERVER_BIN): $(SERVER_SRC)
	GOOS=linux GOARCH=amd64 go build -o $@ $<

build: $(SERVER_BIN)

run: build
	python3 app/main.py

clean:
	rm -f $(SERVER_BIN) .siview-server.hash

.PHONY: build run clean
