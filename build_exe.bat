@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo [1/2] 安装依赖...
python -m pip install -r requirements.txt -q
echo [2/2] PyInstaller 打包...
python -m PyInstaller --noconfirm --clean order_grabber.spec
if errorlevel 1 (
  echo 打包失败
  exit /b 1
)
echo.
echo 完成: dist\电商订单抓取助手\电商订单抓取助手.exe
explorer dist\电商订单抓取助手
