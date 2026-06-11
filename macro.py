import json
import time
import ctypes
from ctypes import wintypes

# --- Windows API 정의 ---
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# 상수 정의
WM_HOTKEY = 0x0312
MOD_NOREPEAT = 0x4000
CF_UNICODETEXT = 13
GHND = 0x0042

# F13 ~ F24의 가상 키 코드 (VK_F13 = 0x7C, ..., VK_F24 = 0x87)
VK_F_KEYS = {f"f{i}": 0x7C + (i - 13) for i in range(13, 25)}

def set_clipboard(text):
    """Windows API를 사용하여 유니코드 텍스트를 클립보드에 복사"""
    buf = text.encode('utf-16-le') + b'\x00\x00'
    h_mem = kernel32.GlobalAlloc(GHND, len(buf))
    p_mem = kernel32.GlobalLock(h_mem)
    ctypes.memmove(p_mem, buf, len(buf))
    kernel32.GlobalUnlock(h_mem)
    
    if user32.OpenClipboard(None):
        user32.EmptyClipboard()
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        user32.CloseClipboard()

def send_paste():
    """Ctrl + V 키 입력을 시뮬레이션"""
    VK_CONTROL = 0x11
    VK_V = 0x56
    KEYEVENTF_KEYUP = 0x0002
    
    # Ctrl Down -> V Down -> V Up -> Ctrl Up
    user32.keybd_event(VK_CONTROL, 0, 0, 0)
    user32.keybd_event(VK_V, 0, 0, 0)
    user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
    user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

# --- 메인 로직 ---

# 1. 설정 로드
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        hotkeys_config = {k.lower(): v for k, v in config.items()}
except Exception as e:
    print(f"설정 파일 오류: {e}")
    exit(1)

# 2. 핫키 등록
registered_ids = {}
for i, (key_name, text) in enumerate(hotkeys_config.items()):
    if key_name in VK_F_KEYS:
        vk = VK_F_KEYS[key_name]
        # RegisterHotKey(hWnd, id, fsModifiers, vk)
        # MOD_NOREPEAT를 사용하여 키를 꾹 누르고 있어도 한 번만 실행되게 함
        if user32.RegisterHotKey(None, i, MOD_NOREPEAT, vk):
            registered_ids[i] = (key_name, text)
            print(f"등록 성공: {key_name} -> {text[:15]}...")
        else:
            print(f"등록 실패: {key_name} (이미 다른 프로그램에서 사용 중일 수 있음)")

if not registered_ids:
    print("등록된 핫키가 없습니다. 프로그램을 종료합니다.")
    exit(1)

print("\n매크로가 실행 중입니다. F13~F24 키를 누르세요.")
print("종료하려면 이 창을 닫거나 Ctrl+C를 누르세요.")

# 3. 메시지 루프 (핫키 감지)
try:
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        if msg.message == WM_HOTKEY:
            hotkey_id = msg.wParam
            if hotkey_id in registered_ids:
                name, content = registered_ids[hotkey_id]
                print(f"[{name}] 감지! 붙여넣기 중...")
                
                set_clipboard(content)
                time.sleep(0.05)
                send_paste()
                
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))
finally:
    # 종료 시 핫키 해제
    for hotkey_id in registered_ids:
        user32.UnregisterHotKey(None, hotkey_id)
