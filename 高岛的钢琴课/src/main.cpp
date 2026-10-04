#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <commctrl.h>
#include <commdlg.h>
#include <shellapi.h>
#include <string>
#include <thread>
#include <memory>
#include <utility>
#include "formats.h"
#include "converter.h"

#pragma comment(lib, "comctl32.lib")
#pragma comment(lib, "comdlg32.lib")
#pragma comment(lib, "shell32.lib")

// 启用 Common Controls 6 视觉样式（现代扁平控件外观）
#pragma comment(linker, "\"/manifestdependency:type='win32' name='Microsoft.Windows.Common-Controls' version='6.0.0.0' processorArchitecture='*' publicKeyToken='6595b64144ccf1df' language='*'\"")

#define IDI_APP 101  // 程序图标资源 ID

enum {
    IDC_PATH        = 1001,
    IDC_BROWSE      = 1002,
    IDC_RADIO_FIRST = 1100, // 1100 .. 1100+kFormatCount-1 对应五种格式
    IDC_STATUS      = 1201,
    IDC_CONVERT     = 1301,
};

#define WM_APP_PROGRESS (WM_APP + 1)
#define WM_APP_DONE     (WM_APP + 2)

// 极简主题色
constexpr COLORREF kAccent         = RGB(0x2F, 0x80, 0xED);
constexpr COLORREF kAccentHover    = RGB(0x3B, 0x8B, 0xF0);
constexpr COLORREF kAccentDown     = RGB(0x1F, 0x5F, 0xC0);
constexpr COLORREF kAccentDisabled = RGB(0xB0, 0xBE, 0xC5);
constexpr COLORREF kTextDark       = RGB(0x33, 0x33, 0x33);
constexpr COLORREF kTextGray       = RGB(0x8A, 0x8A, 0x8A);

HINSTANCE g_hInst;
HFONT     g_font, g_font_bold;
HWND      g_hPath, g_hStatus, g_hConvert, g_hBrowse;
HWND      g_hRadios[kFormatCount];
std::wstring g_input_path, g_ffmpeg_path, g_out_dir;
bool      g_busy = false;
int       g_btn_hover = 0; // 0=无, 1=悬停
WNDPROC   g_btn_proc = nullptr;

// ---------- 工具函数 ----------

static std::wstring exe_dir() {
    wchar_t buf[MAX_PATH];
    GetModuleFileNameW(nullptr, buf, MAX_PATH);
    std::wstring p = buf;
    size_t s = p.find_last_of(L"\\/");
    return (s == std::wstring::npos) ? std::wstring() : p.substr(0, s);
}

static int selected_format_index() {
    for (int i = 0; i < kFormatCount; ++i)
        if (SendMessageW(g_hRadios[i], BM_GETCHECK, 0, 0) == BST_CHECKED) return i;
    return kDefaultFormatIndex;
}

static void open_folder_select(const std::wstring& path) {
    std::wstring param = L"/select,\"" + path + L"\"";
    ShellExecuteW(nullptr, L"open", L"explorer.exe", param.c_str(), nullptr, SW_SHOWNORMAL);
}

// ---------- 交互 ----------

static void on_browse(HWND hwnd) {
    wchar_t file[MAX_PATH * 2] = { 0 };
    OPENFILENAMEW ofn{};
    ofn.lStructSize = sizeof(ofn);
    ofn.hwndOwner = hwnd;
    ofn.lpstrFilter =
        L"视频 / 图片文件\0*.mp4;*.avi;*.mov;*.mkv;*.flv;*.wmv;*.webm;*.m4v;*.mpg;*.mpeg;*.ts;*.m2ts;*.3gp;*.jpg;*.jpeg;*.png;*.bmp;*.gif\0"
        L"所有文件\0*.*\0";
    ofn.lpstrFile = file;
    ofn.nMaxFile = MAX_PATH * 2;
    ofn.Flags = OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_EXPLORER;
    ofn.lpstrTitle = L"选择要提取音频的视频文件";
    if (GetOpenFileNameW(&ofn)) {
        g_input_path = file;
        SetWindowTextW(g_hPath, g_input_path.c_str());
        SetWindowTextW(g_hStatus, L"就绪");
    }
}

// 后台线程：执行转换，进度与结果通过 PostMessage 回主线程
static void conversion_thread(HWND hwnd, std::wstring input, int sel) {
    const AudioFormat& fmt = kAudioFormats[sel];
    std::wstring output = make_output_path(input, fmt.ext, g_out_dir);
    PostMessageW(hwnd, WM_APP_PROGRESS, 0, (LPARAM)new std::wstring(L"正在提取音频…"));

    ConvertResult res = convert_audio(g_ffmpeg_path, input, fmt, output,
        [hwnd](const std::wstring& p) {
            PostMessageW(hwnd, WM_APP_PROGRESS, 0, (LPARAM)new std::wstring(p));
        });

    PostMessageW(hwnd, WM_APP_DONE, 0, (LPARAM)new ConvertResult(std::move(res)));
}

static void on_convert(HWND hwnd) {
    if (g_busy) return;
    if (g_input_path.empty()) {
        SetWindowTextW(g_hStatus, L"请先选择视频文件");
        return;
    }
    if (GetFileAttributesW(g_ffmpeg_path.c_str()) == INVALID_FILE_ATTRIBUTES) {
        SetWindowTextW(g_hStatus, L"未找到 ffmpeg.exe（应位于 bin 目录）");
        return;
    }
    CreateDirectoryW(g_out_dir.c_str(), nullptr);

    g_busy = true;
    EnableWindow(g_hConvert, FALSE);
    EnableWindow(g_hBrowse, FALSE);

    int sel = selected_format_index();
    std::wstring input = g_input_path;
    std::thread(conversion_thread, hwnd, input, sel).detach();
}

// ---------- 自绘「开始转换」按钮 ----------

static void draw_convert_button(const DRAWITEMSTRUCT& di) {
    bool pressed  = (di.itemState & ODS_SELECTED) != 0;
    bool disabled = (di.itemState & ODS_DISABLED) != 0;
    bool hover    = (g_btn_hover == 1) && !pressed && !disabled;
    COLORREF bg = disabled ? kAccentDisabled
               : pressed  ? kAccentDown
               : hover    ? kAccentHover
               : kAccent;

    HDC dc = di.hDC;
    RECT r = di.rcItem;
    HBRUSH br = CreateSolidBrush(bg);
    HPEN pen = CreatePen(PS_SOLID, 1, bg);
    HGDIOBJ ob = SelectObject(dc, br);
    HGDIOBJ op = SelectObject(dc, pen);
    RoundRect(dc, r.left, r.top, r.right, r.bottom, 8, 8);
    SelectObject(dc, ob);
    SelectObject(dc, op);
    DeleteObject(br);
    DeleteObject(pen);

    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, RGB(255, 255, 255));
    HFONT old = (HFONT)SelectObject(dc, g_font_bold);
    RECT tr = r;
    DrawTextW(dc, L"开始转换", -1, &tr, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
    SelectObject(dc, old);
}

static LRESULT CALLBACK convert_btn_proc(HWND hwnd, UINT msg, WPARAM w, LPARAM l) {
    switch (msg) {
    case WM_MOUSEMOVE:
        if (!g_btn_hover) {
            g_btn_hover = 1;
            InvalidateRect(hwnd, nullptr, FALSE);
            TRACKMOUSEEVENT tme{ sizeof(tme), TME_LEAVE, hwnd, 0 };
            TrackMouseEvent(&tme);
        }
        break;
    case WM_MOUSELEAVE:
        g_btn_hover = 0;
        InvalidateRect(hwnd, nullptr, FALSE);
        break;
    }
    return CallWindowProcW(g_btn_proc, hwnd, msg, w, l);
}

// ---------- 窗口构建 ----------

static void on_create(HWND hwnd) {
    INITCOMMONCONTROLSEX icc{ sizeof(icc), ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&icc);

    g_font = CreateFontW(-16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
                         DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                         CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Microsoft YaHei UI");
    g_font_bold = CreateFontW(-16, 0, 0, 0, FW_SEMIBOLD, FALSE, FALSE, FALSE,
                              DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
                              CLEARTYPE_QUALITY, DEFAULT_PITCH, L"Microsoft YaHei UI");

    // 第一行：标签 + 路径 + 浏览
    HWND lbl = CreateWindowW(L"STATIC", L"视频文件", WS_CHILD | WS_VISIBLE,
                             24, 28, 70, 20, hwnd, nullptr, g_hInst, nullptr);
    SendMessageW(lbl, WM_SETFONT, (WPARAM)g_font, TRUE);

    g_hPath = CreateWindowW(L"EDIT", L"", WS_CHILD | WS_VISIBLE | WS_BORDER | ES_READONLY,
                            100, 24, 256, 26, hwnd, (HMENU)(INT_PTR)IDC_PATH, g_hInst, nullptr);
    SendMessageW(g_hPath, WM_SETFONT, (WPARAM)g_font, TRUE);
    SendMessageW(g_hPath, EM_SETCUEBANNER, TRUE, (LPARAM)L"点击右侧按钮选择视频");

    g_hBrowse = CreateWindowW(L"BUTTON", L"浏览…", WS_CHILD | WS_VISIBLE | BS_PUSHBUTTON | WS_TABSTOP,
                              364, 24, 92, 26, hwnd, (HMENU)(INT_PTR)IDC_BROWSE, g_hInst, nullptr);
    SendMessageW(g_hBrowse, WM_SETFONT, (WPARAM)g_font, TRUE);

    // 第二行：输出格式分组
    HWND group = CreateWindowW(L"BUTTON", L"输出格式", WS_CHILD | WS_VISIBLE | BS_GROUPBOX,
                               24, 74, 432, 78, hwnd, nullptr, g_hInst, nullptr);
    SendMessageW(group, WM_SETFONT, (WPARAM)g_font, TRUE);

    for (int i = 0; i < kFormatCount; ++i) {
        DWORD style = WS_CHILD | WS_VISIBLE | BS_AUTORADIOBUTTON | WS_TABSTOP;
        if (i == 0) style |= WS_GROUP;
        int rx = 44 + i * 80;
        g_hRadios[i] = CreateWindowW(L"BUTTON", kAudioFormats[i].name, style,
                                     rx, 102, 68, 22, hwnd,
                                     (HMENU)(INT_PTR)(IDC_RADIO_FIRST + i), g_hInst, nullptr);
        SendMessageW(g_hRadios[i], WM_SETFONT, (WPARAM)g_font, TRUE);
    }
    SendMessageW(g_hRadios[kDefaultFormatIndex], BM_SETCHECK, BST_CHECKED, 0);

    // 第三行：状态栏
    g_hStatus = CreateWindowW(L"STATIC", L"就绪 — 选择视频后点击「开始转换」",
                              WS_CHILD | WS_VISIBLE | SS_LEFT,
                              24, 178, 432, 24, hwnd, (HMENU)(INT_PTR)IDC_STATUS, g_hInst, nullptr);
    SendMessageW(g_hStatus, WM_SETFONT, (WPARAM)g_font, TRUE);

    // 第四行：自绘主按钮
    g_hConvert = CreateWindowW(L"BUTTON", L"",
                               WS_CHILD | WS_VISIBLE | BS_OWNERDRAW | WS_GROUP | WS_TABSTOP | BS_DEFPUSHBUTTON,
                               24, 216, 432, 44, hwnd, (HMENU)(INT_PTR)IDC_CONVERT, g_hInst, nullptr);
    g_btn_proc = (WNDPROC)SetWindowLongPtrW(g_hConvert, GWLP_WNDPROC, (LONG_PTR)convert_btn_proc);
}

// ---------- 主窗口过程 ----------

static LRESULT CALLBACK WndProc(HWND hwnd, UINT msg, WPARAM w, LPARAM l) {
    switch (msg) {
    case WM_CREATE:
        on_create(hwnd);
        return 0;

    case WM_COMMAND: {
        int id = LOWORD(w), code = HIWORD(w);
        if (id == IDC_BROWSE && code == BN_CLICKED) on_browse(hwnd);
        else if (id == IDC_CONVERT && code == BN_CLICKED) on_convert(hwnd);
        return 0;
    }

    case WM_DRAWITEM: {
        LPDRAWITEMSTRUCT di = (LPDRAWITEMSTRUCT)l;
        if (di->CtlID == IDC_CONVERT) { draw_convert_button(*di); return TRUE; }
        break;
    }

    case WM_APP_PROGRESS: {
        std::unique_ptr<std::wstring> p((std::wstring*)l);
        SetWindowTextW(g_hStatus, p->c_str());
        return 0;
    }

    case WM_APP_DONE: {
        g_busy = false;
        EnableWindow(g_hConvert, TRUE);
        EnableWindow(g_hBrowse, TRUE);
        std::unique_ptr<ConvertResult> res((ConvertResult*)l);
        if (res->ok) {
            SetWindowTextW(g_hStatus, (L"完成：" + res->output_path).c_str());
            if (MessageBoxW(hwnd,
                            (L"转换完成！\n\n" + res->output_path + L"\n\n是否打开所在文件夹？").c_str(),
                            L"高岛的钢琴课", MB_ICONINFORMATION | MB_YESNO) == IDYES)
                open_folder_select(res->output_path);
        } else {
            SetWindowTextW(g_hStatus, (L"失败：" + res->message).c_str());
            MessageBoxW(hwnd, (L"转换失败\n\n" + res->message).c_str(),
                        L"高岛的钢琴课", MB_ICONWARNING);
        }
        return 0;
    }

    case WM_CTLCOLORSTATIC: {
        HDC dc = (HDC)w;
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, ((HWND)l == g_hStatus) ? kTextGray : kTextDark);
        return (LRESULT)GetStockObject(WHITE_BRUSH);
    }
    case WM_CTLCOLORBTN: {
        HDC dc = (HDC)w;
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, kTextDark);
        return (LRESULT)GetStockObject(WHITE_BRUSH);
    }
    case WM_ERASEBKGND: {
        RECT rc;
        GetClientRect(hwnd, &rc);
        HBRUSH br = CreateSolidBrush(RGB(255, 255, 255));
        FillRect((HDC)w, &rc, br);
        DeleteObject(br);
        return 1;
    }
    case WM_DESTROY:
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(hwnd, msg, w, l);
}

// ---------- 入口 ----------

int APIENTRY wWinMain(HINSTANCE hInst, HINSTANCE, PWSTR, int) {
    g_hInst = hInst;
    SetProcessDPIAware();

    std::wstring dir = exe_dir();
    g_ffmpeg_path = dir + L"\\bin\\ffmpeg.exe";
    g_out_dir     = dir + L"\\output";

    WNDCLASSEXW wc{};
    wc.cbSize        = sizeof(wc);
    wc.style         = CS_HREDRAW | CS_VREDRAW;
    wc.lpfnWndProc   = WndProc;
    wc.hInstance     = hInst;
    wc.hCursor       = LoadCursorW(nullptr, IDC_ARROW);
    wc.hbrBackground = (HBRUSH)GetStockObject(WHITE_BRUSH);
    wc.lpszClassName = L"VideoToAudioWnd";
    wc.hIcon         = LoadIconW(hInst, MAKEINTRESOURCEW(IDI_APP));
    wc.hIconSm       = wc.hIcon;
    RegisterClassExW(&wc);

    RECT rc{ 0, 0, 480, 290 };
    DWORD style = WS_OVERLAPPED | WS_CAPTION | WS_SYSMENU | WS_MINIMIZEBOX;
    AdjustWindowRectEx(&rc, style, FALSE, 0);
    int w = rc.right - rc.left, h = rc.bottom - rc.top;
    int x = (GetSystemMetrics(SM_CXSCREEN) - w) / 2;
    int y = (GetSystemMetrics(SM_CYSCREEN) - h) / 2;

    HWND hwnd = CreateWindowExW(0, wc.lpszClassName, L"高岛的钢琴课", style,
                                x, y, w, h, nullptr, nullptr, hInst, nullptr);
    if (!hwnd) return 0;
    ShowWindow(hwnd, SW_SHOWNORMAL);
    UpdateWindow(hwnd);

    MSG msg;
    while (GetMessageW(&msg, nullptr, 0, 0) > 0) {
        if (!IsDialogMessageW(hwnd, &msg)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
    }
    return (int)msg.wParam;
}
