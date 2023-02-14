.PHONY: build
build:
	cargo build

.PHONY: format
format:
	cargo fmt

.PHONY: lint
lint:
	cargo clippy -- -Dwarnings && cargo fmt && git diff --exit-code

.PHONY: test
test:
	cargo test
