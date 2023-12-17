import copy
import traceback
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QPushButton, QVBoxLayout, QMainWindow, QLabel, QHBoxLayout, QGridLayout, QScrollBar, QFileDialog, QDesktopWidget
from main import Ui_AIUI
from game_controller import GameController, GameArgs
import websocket
import json

class ACTION:
    PLAY = 0
    DISCARD = 1
    COLOR_CLUE = 2
    RANK_CLUE = 3

class CardButton(QWidget):
    def __init__(self, left_text, right_text, left_color, right_color, active_func, value, choices=None, parent=None):
        super().__init__(parent)
        top_widget = QWidget(self)
        top_widget.setFixedSize(120, 90)

        bottom_widget = QWidget(self)
        bottom_widget.setFixedSize(120, 10)

        layout = QVBoxLayout(self)
        layout.addWidget(top_widget)
        layout.addWidget(bottom_widget)

        self.setLayout(layout)
        self.setFixedSize(120, 100)

        self.left_button = QPushButton(left_text)
        self.right_button = QPushButton(right_text)
        self.value = value

        self.left_color = left_color
        self.right_color = right_color
        self.left_button.setStyleSheet(f"{left_color}; font: bold 36px;")
        self.right_button.setStyleSheet(f"{right_color}; font: bold 36px;")

        self.left_button.clicked.connect(lambda _, xx=value: active_func(xx))
        self.right_button.clicked.connect(lambda _, xx=value: active_func(xx))

        layout = QHBoxLayout(top_widget)
        layout.addWidget(self.left_button)
        layout.addWidget(self.right_button)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

    def highlight(self, lighted):
        if lighted:
            self.left_button.setStyleSheet(f"{self.left_color}; font: bold 45px;")
            self.right_button.setStyleSheet(f"{self.right_color}; font: bold 45px;")
        else:
            self.left_button.setStyleSheet(f"{self.left_color}; font: bold 36px;")
            self.right_button.setStyleSheet(f"{self.right_color}; font: bold 36px;")


class ValueButton(QPushButton):
    def __init__(self, text="", value=None, parent=None):
        super().__init__(text, parent)
        self._value = value

    def set_value(self, value):
        self._value = value

    def get_value(self):
        return self._value

class ClientThread(QThread):
    update_table_ui_sig = pyqtSignal(dict)
    handle_action_sig = pyqtSignal(dict)
    ws_load_sig = pyqtSignal(dict)
    game_start_sig = pyqtSignal(dict)
    table_joined_sig = pyqtSignal(dict)
    game_over_sig = pyqtSignal(dict)

    def __init__(self, url, cookie, parent=None):
        super().__init__(parent)
        self.url = url
        self.cookie = cookie

    def run(self):
        print("Connect to Web Socket")
        try:
            url = self.url
            cookie = self.cookie

            self.commandHandlers = {}
            self.tables = {}
            self.username = ""
            self.ws = None
            self.games = {}

            # Initialize the website command handlers (for the lobby).
            self.commandHandlers["welcome"] = self.welcome
            self.commandHandlers["warning"] = self.warning
            self.commandHandlers["error"] = self.error
            self.commandHandlers["table"] = self.table
            self.commandHandlers["tableList"] = self.table_list
            self.commandHandlers["tableGone"] = self.table_gone
            self.commandHandlers["tableStart"] = self.table_start
            self.commandHandlers["joined"] = self.table_joined
            self.commandHandlers["gameOver"] = self.game_over

            # Initialize the website command handlers (for the game).
            self.commandHandlers["init"] = self.init
            self.commandHandlers["gameAction"] = self.game_action
            self.commandHandlers["gameActionList"] = self.game_action_list

            # Start the WebSocket client.
            print('Connecting to "' + url + '".')

            self.ws = websocket.WebSocketApp(
                url,
                on_message=lambda ws, message: self.websocket_message(ws, message),
                on_error=lambda ws, error: self.websocket_error(ws, error),
                on_open=lambda ws: self.websocket_open(ws),
                on_close=lambda ws: self.websocket_close(ws),
                cookie=cookie,
            )

            self.ws_load_sig.emit({"ws": self.ws})
            self.ws.run_forever()
        except Exception as e:
            traceback.print_exc()

    def websocket_message(self, ws, message):
        # For more information, see:
        # https://github.com/Zamiell/hanabi-live/blob/master/src/websocketMessage.go
        result = message.split(" ", 1)  # Split it into two things
        if len(result) != 1 and len(result) != 2:
            print("error: received an invalid WebSocket message:")
            print(message)
            return

        command = result[0]
        try:
            data = json.loads(result[1])
        except:
            print(
                'error: the JSON data for the command of "' + command + '" was invalid'
            )
            return

        if command in self.commandHandlers:
            print('debug: got command "' + command + '"')
            try:
                self.commandHandlers[command](data)
            except Exception as e:
                print('error: command handler for "' + command + '" failed:', e)
                return
        else:
            print('debug: ignoring command "' + command + '"')
            pass

    def websocket_error(self, ws, error):
        print("Encountered a WebSocket error:", error)

    def websocket_close(self, ws):
        print("WebSocket connection closed.")

    def websocket_open(self, ws):
        print("Successfully established WebSocket connection.")

    # --------------------------------
    # Website Command Handlers (Lobby)
    # --------------------------------

    def welcome(self, data):
        self.username = data["username"]
        self.playingtables = data["playingAtTables"]
        if len(self.playingtables) > 0:
            print("Reload Table")
            tableid = self.playingtables[0]
            self.send(
                "tableReattend",
                {
                    "tableID": tableid,
                },
            )


    def error(self, data):
        # Either we have done something wrong, or something has gone wrong on
        # the server.
        print(data)

    def warning(self, data):
        # We have done something wrong.
        print(data)

    def game_over(self, data):
        self.game_over_sig.emit(data)

    def table_joined(self, data):
        self.table_joined_sig.emit(data)

    def table(self, data):
        self.tables[data["id"]] = data
        self.update_table_ui_sig.emit(self.tables)

    def table_list(self, data_list):
        for data in data_list:
            self.table(data)
        self.update_table_ui_sig.emit(self.tables)

    def table_gone(self, data):
        del self.tables[data["tableID"]]
        self.update_table_ui_sig.emit(self.tables)

    def table_start(self, data):
        # The server has told us that a game that we are in is starting. So,
        # the next step is to request some high-level information about the
        # game (e.g. number of players). The server will respond with an "init"
        # command.
        self.send(
            "getGameInfo1",
            {
                "tableID": data["tableID"],
            },
        )

    # -------------------------------
    # Website Command Handlers (Game)
    # -------------------------------

    def init(self, data):
        #初始化所有游戏的内容
        self.game_start_sig.emit(data)

        # 获得下一步的游戏信息
        self.send(
            "getGameInfo2",
            {
                "tableID": data["tableID"],
            },
        )

    def game_action(self, data):
        self.handle_action(data["action"], data["tableID"])

    def game_action_list(self, data):
        for action in data["list"]:
            self.handle_action(action, data["tableID"])

        self.send(
            "loaded",
            {
                "tableID": data["tableID"],
            },
        )

    def handle_action(self, data, table_id):
        print(
            'debug: got a game action of "%s" for table %d' % (data["type"], table_id)
        )
        self.handle_action_sig.emit(data)

    def send(self, command, data):
        if not isinstance(data, dict):
            data = {}
        self.ws.send(command + " " + json.dumps(data))
        print('debug: sent command "' + command + '"')


class AIWindow(QMainWindow, Ui_AIUI):
    def __init__(self, url, cookie, model_data=None):
        super().__init__()
        self.setupUi(self)
        #self.setFixedSize(1300, 1200)
        self.setWindowTitle("HanabiAIAssitant")

        self.nextstep_btn.setEnabled(False)
        self.prevstep_btn.setEnabled(False)
        self.openhistory_btn.setEnabled(False)

        #连接服务器的线程
        self.worker_thread = ClientThread(url, cookie)
        self.worker_thread.game_over_sig.connect(self.game_over)
        self.worker_thread.update_table_ui_sig.connect(self.update_table_info)
        self.worker_thread.handle_action_sig.connect(self.handle_action)
        self.worker_thread.ws_load_sig.connect(self.ws_load)
        self.worker_thread.game_start_sig.connect(self.game_start)
        self.worker_thread.table_joined_sig.connect(self.table_joined)

        self.enable_active_btn(False)
        self.game_controller = GameController(model_data)
        self.current_loss_card = None
        self.support_variant = [
            "No Variant", "6 Suits", "Black (5 Suits)", "Black (6 Suits)", "Rainbow (5 Suits)", "Rainbow (6 Suits)",
            "Brown (5 Suits)", "Brown (6 Suits)", "Dark Rainbow (6 Suits)", "White (5 Suits)", "White (6 Suits)",
            "Pink (5 Suits)", "Pink (6 Suits)", "Gray (6 Suits)"
        ]

        self.play_btn.clicked.connect(self.play_clicked)
        self.discard_btn.clicked.connect(self.discard_clicked)
        self.clue_btn.clicked.connect(self.clue_clicked)
        self.leave_btn.clicked.connect(self.leave_table_clicked)
        self.draw_state = False #发牌状态
        self.in_table = False

        self.nextstep_btn.clicked.connect(self.next_history_clicked)
        self.prevstep_btn.clicked.connect(self.prev_history_clicked)
        self.openhistory_btn.clicked.connect(self.open_history_clicked)

        self.tables = {}
        self.room_label.setWordWrap(3)

        #连接服务器
        self.worker_thread.start()
        #0表示在房间里,1表示等待中,2表示游戏中
        self.in_room_status = 0

    def send(self, command, data):
        if not isinstance(data, dict):
            data = {}
        self.ws.send(command + " " + json.dumps(data))
        print('debug: sent command "' + command + '"')

    def table_joined(self, data):
        tableID = data['tableID']
        table_info = self.tables[tableID]
        table_id = table_info["id"]
        numPlayers = table_info["numPlayers"]
        variant = table_info["variant"]
        players = table_info["players"]
        name = table_info["name"]
        self.table_id = tableID
        table_str = f"{name}\n 在房间中 ID:{table_id} P:{numPlayers} \n模式:{variant} \n 玩家:{players}"
        self.room_label.setText(table_str)
        self.in_room_status = 1
        self.update_table_info(self.tables)

    def game_over(self, data):
        table_str = f"游戏结束了,点击退出离开房间"
        self.room_label.setText(table_str)

    def handle_action(self, data):
        #游戏状态有以下几种
        #draw
        #clue-staus-turn
        #play-draw-status-turn
        #discard-draw-status-turn
        try:
            if data["type"] == "draw":
                self.init_draw_round -= 1
                self.game_controller.online_handle_draw(data)
                self.update_all_game_info()
                #游戏开始了,唤醒一下
                if self.init_draw_round == 0:
                    self.call_next_round(0)

            elif data["type"] == "play":
                action_str = self.game_controller.online_handle_play(data)
                self.update_all_game_info()
                self.online_action_list.append(action_str)

            elif data["type"] == "discard":
                action_str = self.game_controller.online_handle_discard(data)
                self.update_all_game_info()
                self.online_action_list.append(action_str)

            elif data["type"] == "clue":
                action_str = self.game_controller.online_handle_clue(data)
                self.update_all_game_info()
                for clue_r in self.clue_replace:
                    if clue_r in action_str:
                        action_str = action_str.replace(clue_r, self.clue_replace[clue_r])
                        break
                self.online_action_list.append(action_str)

            elif data["type"] == "turn":
                pid = data["currentPlayerIndex"]
                self.call_next_round(pid)
                self.update_all_game_info()

            elif data["type"] == "status":
                self.game_controller.online_handle_status(data)
                self.update_game_state()
            else:
                print(data)
        except Exception as e:
            print(e)
            traceback.print_exc()

    def ws_load(self, ws):
        self.ws = ws["ws"]

    def game_start(self, data):
        print(data)
        tableID = data["tableID"]
        self.clear_UI()
        try:
            #基础游戏设置
            self.clue_replace = {
                "I0": '红色(I0)',
                "I1": '黄色(I1)',
                "I2": '绿色(I2)',
                "I3": '蓝色(I3)',
                "I4": '紫色(I4)',
                "I5": '青色(I5)',
                "R1": '数字1(R1)',
                "R2": '数字2(R2)',
                "R3": '数字3(R3)',
                "R4": '数字4(R4)',
                "R5": '数字5(R5)',
            }
            colors = [
                (255, 182, 193),  # 淡红
                (255, 255, 224),  # 淡黄
                (144, 238, 144),  # 淡绿
                (173, 216, 230),  # 淡蓝
                (221, 160, 221),  # 淡紫
                (173, 216, 230)  # 淡青
            ]
            self.index_to_color = [f"background-color: rgb{color}" for color in colors]

            table_info = self.tables[tableID]
            table_id = table_info["id"]
            numPlayers = table_info["numPlayers"]
            variant = table_info["variant"]
            players = table_info["players"]
            name = table_info["name"]
            table_str = f"{name}\n 游戏开始 ID:{table_id} P:{numPlayers} \n模式:{variant} \n 玩家:{players}"

            self.room_label.setText(table_str)
            self.in_room_status = 2
            self.update_table_info(self.tables)
            self.online_action_list = []
            self.active_pid = 0
            self.random_start = False
            self.server_game = True
            self.table_id = data["tableID"]
            self.game_actions = []
            self.player_count = data["options"]["numPlayers"]
            self.spectating = data["spectating"]
            self.playerNames = data["playerNames"]
            if self.player_count <= 3:
                self.card_count = 5
            else:
                self.card_count = 4
            self.varient_name = data["options"]["variantName"]
            self.init_draw_round = self.card_count * self.player_count

            self.AI_pids = []
            #AI支持的玩法才会有AI预测
            if self.varient_name in self.support_variant:
                if self.spectating:
                    for i in range(self.player_count):
                        self.AI_pids.append(i)
                else:
                    self.AI_pids = [data["ourPlayerIndex"]]
            else:
                print(f"Unsupported variant: {self.varient_name}")

            game_args = dict(
                players=self.player_count,
                players_card=self.card_count,
                AIplayer=self.AI_pids,
                variant=self.varient_name,
                random_start=False,
                start_card=None,
                allow_drawback=False
            )

            gameconf = GameArgs(**game_args)
            self.game_controller.start_game(gameconf)
            special_dict = self.game_controller.special_dict
            if "Dark Rainbow" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "暗彩虹"
                self.index_to_color[special_dict.last_special_card] = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF0000, stop:0.17 #FF7F00, stop:0.33 #FFFF00, stop:0.50 #00FF00, stop:0.67 #0000FF, stop:0.83 #4B0082, stop:1 #9400D3);"
            elif "Rainbow" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "彩虹"
                self.index_to_color[special_dict.last_special_card] = "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FFB6C1, stop:0.17 #FFE4C4, stop:0.33 #FFFFE0, stop:0.50 #98FB98, stop:0.67 #ADD8E6, stop:0.83 #E6E6FA, stop:1 #E3E3E3);"
            elif "Brown" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "棕色"
                self.index_to_color[special_dict.last_special_card] = f"background-color: rgb(205, 133, 63)"
            elif "Black" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "黑色"
                self.index_to_color[special_dict.last_special_card] = f"background-color: rgb(64, 64, 64)"
            elif "White" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "白色"
                self.index_to_color[special_dict.last_special_card] = f"background-color: rgb(250, 250, 250)"
            elif "Pink" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "粉色"
                self.index_to_color[special_dict.last_special_card] = f"background-color: rgb(255, 182, 193)"
            elif "Gray" in self.varient_name:
                self.clue_replace[f"I{special_dict.last_special_card}"] = "灰色"
                self.index_to_color[special_dict.last_special_card] = f"background-color: rgb(220, 220, 220)"
            self.setup_button_pannel(self.player_count)

        except Exception as e:
            print("ERROR:", e)
            traceback.print_exc()
            return

    def open_history_clicked(self):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_name, _ = QFileDialog.getOpenFileName(self, 'Open File', '', 'JSON Files (*.json);;All Files (*)', options=options)
        if file_name:
            # 打开文件并读取内容
            with open(file_name, 'r') as file:
                try:
                    # 解析JSON内容
                    self.clear_UI()
                    history_data = json.load(file)
                    file_name = f"{file_name}"
                    file_name = file_name.replace("ERROR_","")
                    game_args = file_name.split("_")
                    print(game_args)
                    fake_game_data = {
                        "tableID": 1,
                        "spectating": True,
                        "playerNames": ["AI0","AI1","AI2","AI3","AI4","AI5"],
                        "options":{
                            "numPlayers": int(game_args[1][0]),
                            "variantName": game_args[0].split("/")[-1],
                        }
                    }
                    self.game_start(fake_game_data)
                    self.current_history_index = 0
                    self.game_controller.game_history = history_data

                    action = self.game_controller.set_current_history(self.current_history_index)
                    #print("Update History")
                    self.update_all_game_info()
                    #print("update_all_game_info")
                    self.info_label.setText(f'选择操作: {action["str"]}')
                    #print("setText")
                except Exception as e:
                    print(f'Error reading history: {e}')
                    traceback.print_exc()

    def next_history_clicked(self):
        if self.current_history_index < len(self.game_controller.game_history) - 1:
            self.current_history_index += 1
        action = self.game_controller.set_current_history(self.current_history_index)
        self.active_pid = self.game_controller.active_pid
        self.update_all_game_info()
        self.info_label.setText(f'选择操作: {action["str"]}')

    def prev_history_clicked(self):
        if self.current_history_index > 0:
            self.current_history_index -= 1
        action = self.game_controller.set_current_history(self.current_history_index)
        self.active_pid = self.game_controller.active_pid
        self.update_all_game_info()
        self.info_label.setText(f'选择操作: {action["str"]}')


    def ai_action_clicked(self, action_detail):
        act_type = action_detail["type"]
        if act_type == "play":
            pid = action_detail["pid"]
            pos = action_detail["pos"]
            if pid != self.active_pid:
                print("ERROR: 不能操作非当前回合玩家的牌")
                return
            order = self.game_controller.players[pid].online_order[pos]
            self.send(
                "action",
                {
                    "tableID": self.table_id,
                    "type": ACTION.PLAY,
                    "target": order,
                },
            )
        elif act_type == "discard":
            pid = action_detail["pid"]
            pos = action_detail["pos"]
            if pid != self.active_pid:
                print("ERROR: 不能操作非当前回合玩家的牌")
                return
            order = self.game_controller.players[pid].online_order[pos]
            self.send(
                "action",
                {
                    "tableID": self.table_id,
                    "type": ACTION.DISCARD,
                    "target": order,
                },
            )
        elif act_type == "clue":
            from_pid = action_detail["from"]
            to_pid = action_detail["to"]
            clue_type = action_detail["clue_type"]
            clue_value = action_detail["clue_value"]
            if clue_type == 0:
                clue_type = ACTION.COLOR_CLUE
            else:
                clue_type = ACTION.RANK_CLUE
            self.send(
                "action",
                {
                    "tableID": self.table_id,
                    "type": clue_type,
                    "target": to_pid,
                    "value": clue_value,
                },
            )

    def leave_table_clicked(self):
        try:
            if self.in_room_status == 2:
                #游戏已经开始,暴力退出
                self.send(
                    "tableUnattend",
                    {
                        "tableID": self.table_id,
                    },
                )
            elif self.in_room_status == 1:
                #游戏还没开始,退出房间
                self.send(
                    "tableLeave",
                    {
                        "tableID": self.table_id,
                    },
                )
            # 清空游戏相关的所有内容
            self.in_room_status = 0
            self.update_table_info(self.tables)
            self.info_label.setText("游戏未开始")
            self.state_label.setText("无游戏")
            self.room_label.setText("不在房间里")
            self.clear_UI()
        except Exception:
            traceback.print_exc()

    def clear_UI(self):
        a = QWidget()
        self.cards_area.setWidget(a)
        a = QWidget()
        self.AIpredict_area.setWidget(a)
        a = QWidget()
        self.discard_area.setWidget(a)
        a = QWidget()
        self.history_area.setWidget(a)
        while self.Layout_Clue.count():
            item = self.Layout_Clue.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        while self.Layout_score.count():
            item = self.Layout_score.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        while self.Layout_toP.count():
            item = self.Layout_toP.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def join_table_click(self, table_id):
        password = self.password_edit.toPlainText()
        password = password.strip()
        table = self.tables[table_id]
        if table["running"]:
            #游戏已经开始,进入观战
            print("Try tableSpectate")
            self.send(
                "tableSpectate",
                {
                    "shadowingPlayerIndex": -1,
                    "tableID": table_id
                },
            )
        else:
            #正常加入
            if table["passwordProtected"]:
                self.send(
                    "tableJoin",
                    {
                        "tableID": table_id,
                        "password": password
                    },
                )
            else:
                self.send(
                    "tableJoin",
                    {
                        "tableID": table_id,
                    },
                )

    def update_table_info(self, tables):
        try:
            self.tables = tables
            lc = QHBoxLayout()
            for table in tables.values():
                table_id = table["id"]
                numPlayers = table["numPlayers"]
                running = table["running"]
                variant = table["variant"]
                passwordProtected = table["passwordProtected"]
                players = table["players"]
                name = table["name"]

                table_str = f"[{name}]  \n" \
                            f"ID:{table_id} | 玩家数: {numPlayers} | 游戏中: {running} \n" \
                            f"模式: {variant} \n" \
                            f"密码: {passwordProtected} \n" \
                            f"[{','.join(players)}]"

                cbutton = QPushButton(table_str)
                cbutton.setFixedSize(300, 140)
                cbutton.setStyleSheet(f"text-align: center; font: 15px;")
                cbutton.clicked.connect(lambda _, xx=table_id: self.join_table_click(xx))
                if self.in_room_status != 0:
                    cbutton.setEnabled(False)
                else:
                    cbutton.setEnabled(True)

                lc.addWidget(cbutton)

            lc.addStretch(1)
            a = QWidget()
            a.setLayout(lc)
            self.table_area.setWidget(a)
        except Exception as e:
            traceback.print_exc()

    def enable_active_btn(self, enable):
        self.discard_btn.setEnabled(enable)
        self.play_btn.setEnabled(enable)
        self.clue_btn.setEnabled(enable)

    def play_clicked(self):
        if self.current_pcard_pid_pos is None:
            print("ERROR: 没有选中的玩家牌")
            return
        [pid, pos] = self.current_pcard_pid_pos
        if pid != self.active_pid:
            print("ERROR: 不能操作非当前回合玩家的牌")
            return
        order = self.game_controller.players[pid].online_order[pos]
        self.send(
            "action",
            {
                "tableID": self.table_id,
                "type": ACTION.PLAY,
                "target": order,
            },
        )

    def discard_clicked(self):
        if self.current_pcard_pid_pos is None:
            print("ERROR: 没有选中的玩家牌")
            return
        [pid, pos] = self.current_pcard_pid_pos
        if pid != self.active_pid:
            print("ERROR: 不能操作非当前回合玩家的牌")
            return
        order = self.game_controller.players[pid].online_order[pos]
        self.send(
            "action",
            {
                "tableID": self.table_id,
                "type": ACTION.DISCARD,
                "target": order,
            },
        )

    def clue_clicked(self):
        try:
            if self.clue_choose is None:
                print("ERROR: 还没有选择提示")
                return
            if self.splayer_choose is None:
                print("ERROR: 还没有选择提示的玩家")
                return
            rpid = self.splayer_choose - self.active_pid
            if rpid < 0:
                rpid += self.player_count
            if self.clue_choose[0] == "I":
                clue_type = ACTION.COLOR_CLUE
            else:
                clue_type = ACTION.RANK_CLUE
            self.send(
                "action",
                {
                    "tableID": self.table_id,
                    "type": clue_type,
                    "target": self.splayer_choose,
                    "value": int(self.clue_choose[1]),
                },
            )
        except Exception as e:
            print(e)
            traceback.print_exc()

    def call_next_round(self, active_pid):
        try:
            lb = QVBoxLayout()
            self.active_pid = active_pid
            self.info_label.setText(f"轮到P{active_pid}【{self.playerNames[active_pid]}】操作")
            if len(self.AI_pids) > 0:
                if active_pid == self.AI_pids[0] and (not self.spectating):
                    self.info_label.setText(f"轮到P{active_pid}【{self.playerNames[active_pid]}】【你自己！】操作")

            if active_pid in self.AI_pids:
                #向AI查询预测结果
                if not self.spectating:
                    self.enable_active_btn(True)
                action_predict = self.game_controller.call_AI_predict(active_pid, 10)
                for action in action_predict:
                    action_token = action["token"]
                    action_probs = action["probs"]
                    action_detail = self.game_controller.get_action(action_token, active_pid)
                    action_desc = action_detail["str"]
                    for clue_r in self.clue_replace:
                        if clue_r in action_desc:
                            #print(clue_r)
                            action_desc = action_desc.replace(clue_r, self.clue_replace[clue_r])
                            break
                    action_str = f'{action_desc} \n 概率:{action_probs*100:.2f}%'
                    actionbutton = ValueButton(action_str, action_detail)
                    actionbutton.setStyleSheet(f"font: bold 18px;")
                    actionbutton.setFixedSize(330, 50)
                    actionbutton.clicked.connect(lambda _, i=copy.deepcopy(action_detail): self.ai_action_clicked(i))
                    if self.spectating:
                        actionbutton.setEnabled(False)
                    else:
                        actionbutton.setEnabled(True)
                    lb.addWidget(actionbutton)
            else:
                self.enable_active_btn(False)

            lb.addStretch(1)
            a = QWidget()
            a.setLayout(lb)
            self.AIpredict_area.setWidget(a)
            print("Call_next_round Finish")
        except Exception as e:
            print(e)
            traceback.print_exc()

    def update_game_state(self):
        state_txt = f"得分:{self.game_controller.score}/{sum(self.game_controller.Hrank)}\n线索:{self.game_controller.clue}" \
                    f"\n 错误:{self.game_controller.mistake} \n 剩余牌:{self.game_controller.get_current_card()}"
        self.state_label.setText(state_txt)

    def update_all_game_info(self):

        self.player_card_btns = []
        self.current_pcard_pid_pos = None

        # 更新所有的分数信息
        for i in range(len(self.game_controller.Irank)):
            score = self.game_controller.Irank[i]
            self.scoreLabels[i].setText(f"{score}")

        #更新历史消息
        lb = QVBoxLayout()
        for history_str in self.online_action_list:
            button = QPushButton(f"{history_str}", self)
            button.setFixedSize(200, 40)
            lb.addWidget(button)
        lb.addStretch(1)
        a = QWidget()
        a.setLayout(lb)

        self.history_area.setWidget(a)

        v_scrollbar = self.history_area.findChild(QScrollBar)
        if v_scrollbar:
            v_scrollbar.setValue(v_scrollbar.maximum())

        #更新弃牌堆信息
        lg = QGridLayout()
        ind = 0
        for card in self.game_controller.discard_cards:
            row = ind // 6
            column = ind % 6
            ind += 1
            card_index, card_rank = self.game_controller.parse_card(card)
            button = QPushButton(f"{card_rank}", self)
            button.setFixedSize(40, 40)
            button.setStyleSheet(f"{self.index_to_color[card_index]}; font: bold 24px;")
            lg.addWidget(button, row, column)
        #lg.addStretch(1)
        a = QWidget()
        a.setLayout(lg)
        self.discard_area.setWidget(a)

        # 更新UI中玩家的卡
        lb = QVBoxLayout()
        pid = 0
        for player in self.game_controller.players:
            p_head = QLabel(f"Player: {pid} [{self.playerNames[pid]}]")
            if pid == self.active_pid:
                p_head.setStyleSheet(f'font: bold 35px;')
            else:
                p_head.setStyleSheet(f'font-size: 30px;')
            lb.addWidget(p_head)
            cl = len(player.cards)
            lc = QHBoxLayout()
            for i in range(cl - 1, -1, -1):
                card = player.cards[i]
                kcard = player.known_cards[i]
                card_index, card_rank = self.game_controller.parse_card(card)
                kcard_index, kcard_rank = self.game_controller.parse_card(kcard)
                if card_index == 9:
                    card_color = "background-color: rgb(200, 200, 200)"
                else:
                    card_color = self.index_to_color[card_index]
                if kcard_index == 9:
                    kcard_color = "background-color: rgb(200, 200, 200)"
                else:
                    kcard_color = self.index_to_color[kcard_index]
                if card_rank == 9:
                    card_rank = "?"
                if kcard_rank == 9:
                    kcard_rank = "?"

                pcbutton = CardButton(f"{card_rank}", f"{kcard_rank}", card_color, kcard_color, self.pcard_clicked, [pid, i])
                self.player_card_btns.append(pcbutton)
                #self.current_tbutton_list.append(pcbutton)
                lc.addWidget(pcbutton)

            pid += 1
            lc.addStretch(0)
            lb.addLayout(lc)

        lb.addStretch(1)
        a = QWidget()
        a.setLayout(lb)
        self.cards_area.setWidget(a)

    def playerchose_clicked(self, pid):
        self.splayer_choose = pid
        for cbtn in self.splayer_btns:
            if cbtn.get_value() == pid:
                cbtn.setStyleSheet(cbtn.styleSheet().replace("24px;", "36px;"))
            else:
                cbtn.setStyleSheet(cbtn.styleSheet().replace("36px;", "24px;"))

    def cluechose_clicked(self, clue):
        self.clue_choose = clue
        for cbtn in self.clue_btns:
            if cbtn.get_value() == clue:
                cbtn.setStyleSheet(cbtn.styleSheet().replace("24px;", "36px;"))
            else:
                cbtn.setStyleSheet(cbtn.styleSheet().replace("36px;", "24px;"))

    def pcard_clicked(self, pid_pos):
        self.current_pcard_pid_pos = pid_pos
        #print(self.current_pcard_pid_pos)
        for cbtn in self.player_card_btns:
            #print(cbtn.get_value())
            if cbtn.value[0] == pid_pos[0] and cbtn.value[1] == pid_pos[1]:
                cbtn.highlight(True)
            else:
                cbtn.highlight(False)

    def setup_button_pannel(self, players):
        #选择玩家区域的所有玩家
        self.splayer_btns = []
        self.splayer_choose = None
        for i in range(0, players):
            button = ValueButton(f"P{i}", i)
            button.setFixedSize(60, 60)

            button.setStyleSheet(f"background-color: rgb(220, 220, 220); font: bold 24px;")
            self.splayer_btns.append(button)

            button.clicked.connect(lambda _, i=i: self.playerchose_clicked(i))
            self.Layout_toP.addWidget(button, i)

        #选择提示线索区域的所有线索
        self.clue_btns = []
        self.clue_choose = None
        special_dict = self.game_controller.special_dict
        colors = special_dict.last_special_card + 1
        for i in range(colors):
            #提示颜色
            if i == special_dict.last_special_card and (special_dict.all_color_rule or special_dict.no_color_rule):
                #彩虹无法被提示,Null也无法被提示
                continue
            clue = f"I{i}"
            button = ValueButton(clue, clue)
            button.setFixedSize(50, 50)

            button.setStyleSheet(f"{self.index_to_color[i]}; font: bold 24px;")
            self.clue_btns.append(button)

            button.clicked.connect(lambda _, clue=clue: self.cluechose_clicked(clue))
            self.Layout_Clue.addWidget(button, 0, i)
        for i in range(1, 6):
            #提示数字
            clue = f"R{i}"
            button = ValueButton(clue, clue)
            button.setFixedSize(50, 50)

            button.setStyleSheet(f"background-color: rgb(200, 200, 200); font: bold 24px;")
            self.clue_btns.append(button)

            button.clicked.connect(lambda _, clue=clue: self.cluechose_clicked(clue))
            self.Layout_Clue.addWidget(button, 1, i - 1)

        #得分区域的显示(对应五种颜色)
        self.scoreLabels = []
        for i in range(colors):
            #提示颜色
            clue = f"I{i}"
            sl = QLabel("0")
            sl.setFixedSize(70, 70)
            sl.setStyleSheet("QLabel {"
                             f"{self.index_to_color[i]};"
                             "border: 2px solid black;"
                             "border-radius: 5px;"
                             "font: bold 40px;"
                             "text-align: center;"
                             "}")
            self.scoreLabels.append(sl)
            self.Layout_score.addWidget(sl, i)



