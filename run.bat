@echo off
echo ===================================================
echo    أداة استخراج بيانات البريد الإلكتروني
echo ===================================================
echo.

REM التحقق من وجود بيئة Python
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo خطأ: لم يتم العثور على Python. يرجى تثبيت Python 3.6 أو أحدث.
    echo يمكنك تنزيل Python من https://www.python.org/downloads/
    pause
    exit /b 1
)

REM التحقق من إصدار Python
for /f "tokens=2" %%I in ('python --version 2^>^&1') do set PYTHON_VERSION=%%I
echo تم العثور على Python إصدار %PYTHON_VERSION%

REM التحقق من وجود المكتبات المطلوبة وتثبيتها إذا لزم الأمر
echo جاري التحقق من المكتبات المطلوبة...
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
    echo خطأ: فشل تثبيت المكتبات المطلوبة.
    pause
    exit /b 1
)

echo تم تثبيت جميع المكتبات المطلوبة بنجاح.
echo.

REM تشغيل الخادم
echo جاري تشغيل خادم أداة استخراج بيانات البريد الإلكتروني...
echo يمكنك الوصول إلى التطبيق من خلال فتح المتصفح والانتقال إلى العنوان التالي:
echo http://localhost:5000
echo.
echo اضغط Ctrl+C لإيقاف الخادم.
echo.

python server.py

pause