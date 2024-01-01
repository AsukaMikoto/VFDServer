import serial
import json
from flask import Flask,make_response
from flask import request

app = Flask(__name__)

temp = ''
# 編碼轉換用
def Text2ShiftJIS_Hex(text):
    result = ''
    # 轉換失敗的字
    global temp
    # clear
    temp = ''
    for i in range(0,len(text)):
        try:
            hex_str = str(text[i].encode('shift_jis').hex())
        except:
            temp = text[i]
            return ''
        hex_str_result = hex_str[0:2] + ' ' + hex_str[2:]+' '
        result += hex_str_result
    return result + '20 20'

# 这里的参数需要改成你的实际参数
VFD_PORT = 'COM3'
VFD_BAUDRATE = 115200
# 發炮
def sendText(text:list, isScroll:bool):
    # 连接
    ser = serial.Serial(VFD_PORT, VFD_BAUDRATE)
    # PowerON
    hex_command = bytes.fromhex('1b 0b')
    ser.write(hex_command)
    # Boot
    hex_command = bytes.fromhex('1b 21 01')
    ser.write(hex_command)
    # Set Language
    hex_command = bytes.fromhex('1b 32 02')
    ser.write(hex_command)
    # Clear
    hex_command = bytes.fromhex('1b 0c')
    ser.write(hex_command)
    # Stop Scroll
    hex_command = bytes.fromhex('1b 52')
    ser.write(hex_command)
    # Set Option
    hex_command = bytes.fromhex('1b 40 00 00 {} 00 9f 02'.format('02' if len(text)==2 else '00'))
    ser.write(hex_command)
    # Set Speed
    hex_command = bytes.fromhex('1b 41 00')
    ser.write(hex_command)

    # text
    # 單行
    if len(text) == 1:
        text1 = Text2ShiftJIS_Hex(text[0])
        size_hex = hex(0).replace('x','')
        if isScroll:
            size_hex = format(int(len(text1.replace(' ',''))/2), '02X')
        text_command = '1b 50 {} {}'.format(size_hex, text1)
        hex_command = bytes.fromhex(text_command)
        ser.write(hex_command)
    # 雙行
    elif len(text) == 2:
        # text1 第一行的内容
        text1 = Text2ShiftJIS_Hex(text[0])
        text1 = '20 20 ' + text1

        # 双行模式不判断是否滚动，不滚动的情况下显示有bug
        size_hex = format(int(len(text1.replace(' ',''))/2), '02X')

        text_command = '1b 30 {} {}'.format(size_hex, text1)
        hex_command = bytes.fromhex(text_command)
        ser.write(hex_command)
        # text2 第二行的内容
        text2 = Text2ShiftJIS_Hex(text[1])

        # 双行模式不判断是否滚动，不滚动的情况下显示有bug
        size_hex = format(int(len(text2.replace(' ',''))/2), '02X')

        text_command = '1b 50 {} {}'.format(size_hex, text2)
        hex_command = bytes.fromhex(text_command)
        ser.write(hex_command)
    else:
        return {'status':0, 'message': '發送失敗!VFD只有二行可顯示區域!'}
    #check unsupport charset
    global temp
    if temp != '':
        return {'status':-1, 'message': '有ShiftJIS中不支援的文字 \'{}\' 請修改!'.format(temp)}
    # Start Scroll
    hex_command = bytes.fromhex('1b 51')
    ser.write(hex_command)
    #close serial
    ser.close()

    return {'status':1, 'message': '發送成功!'}

# 写成Http POST接口 方便第三方程序调用改写内容
# 参数1 text 类型list 可以发送['Test'] 一行，['Test','123456'] 双行
# 参数2 isScroll 是否滚动显示 仅单行模式下有效 双行强制滚动。
@app.route('/sendText',methods = ['POST'])
def vfd_sendtext_api():
    param = request.get_json()
    if param.get('text') == None:
        sendText(['文字參數不存在'],False)
        return make_response(json.dumps({'status':-2, 'message': '發送失敗!文字參數不存在!'}))
    if isinstance(param.get('text'), list) == False:
        sendText(['文字參數不是列表'],False)
        return make_response(json.dumps({'status':-3, 'message': '發送失敗!文字參數不是列表!'}))
    # 如果沒提供是否捲動 都不捲動
    isScroll = False
    if param.get('isScroll') != None:
        isScroll = param['isScroll']
    result = sendText(param.get('text'), isScroll)
    print(result)
    if result['status'] == -1:
        sendText(['有不支援的文字'], False)
    elif result['status'] == 0:
        sendText(['發送失敗 超行'], False)
    
    return make_response(json.dumps(result))

# 给扫描机器人使用的请求 所有不存在的URI都返回403
@app.route('/<path>',methods = ['GET','POST'])
def noAuthentication(path = ''):
    return '',403

# flask初始化用 可以在下面改成你的局域网地址以及你喜欢的端口号
if __name__ == '__main__':
    host = '127.0.0.1'
    port = 8100
    app.run(host=host,port=port)