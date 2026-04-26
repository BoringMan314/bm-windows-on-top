bm-windows-on-top Win7 使用說明
===========================

本版本適用於 Windows 7 SP1。

1) 請先安裝 Windows 7 必要系統更新：
   - KB2533623
   - KB2999226（Universal CRT）

2) 請安裝 Microsoft Visual C++ Redistributable 2015-2022
   （x86 或 x64 請依你的作業系統版本選擇）。

3) 完成後執行：
   - bm-windows-on-top_win7.exe

若啟動時仍出現缺少 api-ms-win-core-*.dll：
 - 代表你的 Windows 7 尚未完成上述更新。
 - 請安裝更新後重新開機，再次執行 EXE。

打包鏈要求：
 - Win7 版本執行檔必須使用 Python 3.8（或更低版本）打包。
