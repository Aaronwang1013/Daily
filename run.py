"""
本地啟動腳本
執行方式：python run.py
Dashboard 網址：http://localhost:8000
API 文件：http://localhost:8000/docs
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,      # 儲存檔案後自動重啟，開發時很方便
    )
