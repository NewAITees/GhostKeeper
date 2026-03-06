BACKEND_PORT := 18000
FRONTEND_PORT := 5173
BACKEND_LOG  := /tmp/ghostkeeper_backend.log
FRONTEND_LOG := /tmp/ghostkeeper_frontend.log
PID_FILE     := /tmp/ghostkeeper.pids

.PHONY: dev stop logs install

## 両サービスを同時起動
dev: stop
	@echo "==> バックエンド起動 (port $(BACKEND_PORT))..."
	@cd backend && uv run uvicorn app.main:app --reload --port $(BACKEND_PORT) > $(BACKEND_LOG) 2>&1 & echo $$! >> $(PID_FILE)
	@echo "==> フロントエンド起動 (port $(FRONTEND_PORT))..."
	@cd frontend && npm run dev > $(FRONTEND_LOG) 2>&1 & echo $$! >> $(PID_FILE)
	@sleep 3
	@echo ""
	@echo "  Backend  : http://localhost:$(BACKEND_PORT)/api/health"
	@echo "  Frontend : http://localhost:$(FRONTEND_PORT)"
	@echo ""
	@echo "ログ確認: make logs"
	@echo "停止    : make stop"

## 両サービスを停止
stop:
	@if [ -f $(PID_FILE) ]; then \
		echo "==> GhostKeeper を停止します..."; \
		while IFS= read -r pid; do \
			kill "$$pid" 2>/dev/null && echo "  PID $$pid 停止" || true; \
		done < $(PID_FILE); \
		rm -f $(PID_FILE); \
	fi
	@lsof -ti:$(BACKEND_PORT) | xargs kill -9 2>/dev/null || true
	@lsof -ti:$(FRONTEND_PORT) | xargs kill -9 2>/dev/null || true

## ログをリアルタイム表示
logs:
	@echo "=== Backend ===" && tail -f $(BACKEND_LOG) &
	@echo "=== Frontend ===" && tail -f $(FRONTEND_LOG)

## 依存パッケージインストール
install:
	@echo "==> backend dependencies..."
	@cd backend && uv sync
	@echo "==> frontend dependencies..."
	@cd frontend && npm install
	@echo "==> 完了"
