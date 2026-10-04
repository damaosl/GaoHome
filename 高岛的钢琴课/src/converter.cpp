#include "converter.h"
#include <windows.h>
#include <string>
#include <vector>

static std::wstring quote(const std::wstring& s) {
    return L"\"" + s + L"\"";
}

std::wstring make_output_path(const std::wstring& input,
                              const wchar_t* ext,
                              const std::wstring& out_dir) {
    // 提取输入文件名（不含目录）
    std::wstring base = input;
    size_t slash = base.find_last_of(L"\\/");
    if (slash != std::wstring::npos) base = base.substr(slash + 1);
    // 去掉扩展名
    size_t dot = base.find_last_of(L'.');
    if (dot != std::wstring::npos) base = base.substr(0, dot);

    std::wstring dir = out_dir;
    if (!dir.empty() && dir.back() != L'\\' && dir.back() != L'/') dir += L'\\';

    std::wstring path = dir + base + L"." + ext;
    for (int i = 1; GetFileAttributesW(path.c_str()) != INVALID_FILE_ATTRIBUTES; ++i)
        path = dir + base + L"_" + std::to_wstring(i) + L"." + ext;
    return path;
}

ConvertResult convert_audio(const std::wstring& ffmpeg_path,
                            const std::wstring& input,
                            const AudioFormat& fmt,
                            const std::wstring& output,
                            const ProgressFn& on_progress) {
    ConvertResult res;
    res.output_path = output;

    // ffmpeg -hide_banner -nostdin -y -i "输入" -vn <编码参数> "输出"
    std::wstring cmd = quote(ffmpeg_path) + L" -hide_banner -nostdin -y -i " +
                       quote(input) + L" -vn " + fmt.ff_args + L" " + quote(output);

    std::vector<wchar_t> cmdline(cmd.begin(), cmd.end());
    cmdline.push_back(L'\0');

    SECURITY_ATTRIBUTES sa{ sizeof(sa), nullptr, TRUE };
    HANDLE rd = nullptr, wr = nullptr;
    if (!CreatePipe(&rd, &wr, &sa, 0)) {
        res.message = L"无法创建输出管道";
        return res;
    }
    SetHandleInformation(rd, HANDLE_FLAG_INHERIT, 0);

    STARTUPINFOW si{};
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESTDHANDLES | STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    si.hStdOutput = wr;
    si.hStdError  = wr;
    si.hStdInput  = GetStdHandle(STD_INPUT_HANDLE);

    PROCESS_INFORMATION pi{};
    if (!CreateProcessW(nullptr, cmdline.data(), nullptr, nullptr, TRUE,
                        CREATE_NO_WINDOW, nullptr, nullptr, &si, &pi)) {
        CloseHandle(rd);
        CloseHandle(wr);
        res.message = L"无法启动 ffmpeg.exe";
        return res;
    }
    CloseHandle(wr);

    // 读取 stderr，解析 time= 进度
    std::string buf;
    char tmp[4096];
    std::wstring last_progress;

    for (;;) {
        DWORD avail = 0;
        if (PeekNamedPipe(rd, nullptr, 0, nullptr, &avail, nullptr) && avail > 0) {
            DWORD n = 0;
            if (ReadFile(rd, tmp, (DWORD)sizeof(tmp) - 1, &n, nullptr) && n > 0) {
                tmp[n] = 0;
                buf.append(tmp, n);
                if (buf.size() > (1u << 20)) buf.erase(0, buf.size() / 2); // 防无限增长
                size_t pos = buf.rfind("time=");
                if (pos != std::string::npos && buf.size() >= pos + 5) {
                    size_t end = pos + 13; // "HH:MM:SS"
                    if (end > buf.size()) end = buf.size();
                    std::wstring wt(buf.begin() + pos + 5, buf.begin() + end);
                    if (wt.size() >= 8) wt = wt.substr(0, 8);
                    if (wt != last_progress && on_progress) {
                        last_progress = wt;
                        on_progress(L"转换中 " + wt);
                    }
                }
            }
        }
        DWORD code = 0;
        if (!GetExitCodeProcess(pi.hProcess, &code)) break;
        if (code != STILL_ACTIVE) break;
        Sleep(50);
    }
    WaitForSingleObject(pi.hProcess, INFINITE);
    DWORD code = 0;
    GetExitCodeProcess(pi.hProcess, &code);

    CloseHandle(rd);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    if (code == 0 && GetFileAttributesW(output.c_str()) != INVALID_FILE_ATTRIBUTES) {
        res.ok = true;
        res.message = L"转换完成";
    } else {
        res.ok = false;
        std::wstring msg = L"转换失败（可能该文件不含音轨）";
        size_t p = buf.find_last_of('\n');
        if (p != std::string::npos) {
            std::string last = buf.substr(p + 1);
            while (!last.empty() &&
                   (last.back() == '\r' || last.back() == '\n' || last.back() == ' '))
                last.pop_back();
            if (!last.empty()) msg.assign(last.begin(), last.end());
        } else if (!buf.empty()) {
            msg.assign(buf.begin(), buf.end());
        }
        res.message = msg;
    }
    return res;
}
