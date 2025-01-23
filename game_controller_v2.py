from play_util import load_model, generate_answer
from dataclasses import dataclass
from game_utils import GameArgs
import random
import math
import traceback
import logging

@dataclass
class SpecialGameArgs:
    no_color_rule: bool = False
    all_color_rule: bool = False
    no_rank_rule: bool = False
    all_rank_rule: bool = False
    last_special_card: int = 4

def try_start_game(gameargs: GameArgs):

    return GameController(gameargs)


class GamePlayer():
    def __init__(self, pid, game_controller):
        self.cards = []
        self.known_cards = []
        self.online_order = []
        self.pid = pid
        self.game_controller = game_controller

    def gain_card(self, card, order=None):
        self.cards.append(card)
        self.online_order.append(order)
        self.known_cards.append("I_R_")

    def get_light_card(self, rpid):
        light_tokens = []
        token = f"light-PR{rpid}"
        light_tokens.append(token)
        for i in range(len(self.cards)):
            lcard = self.cards[i]
            kcard = self.known_cards[i]
            token = f"light-{lcard}-{kcard}"
            light_tokens.append(token)
        return light_tokens

    def get_light_card_myself(self):
        light_tokens = []
        token = f"light-PR0"
        light_tokens.append(token)
        for i in range(len(self.cards)):
            kcard = self.known_cards[i]
            token = f"light-myself-{kcard}"
            light_tokens.append(token)
        return light_tokens

    def get_card_at(self, index):
        return self.cards[index], self.known_cards[index]

    def remove_card_at(self, index):
        self.cards.pop(index)
        self.known_cards.pop(index)
        self.online_order.pop(index)

    def get_clue(self, clue, clue_type, clue_value):
        # clue的格式是一个 I_ 或者 R_
        for card_ind in range(len(self.cards)):
            # print(clue_info, target_card[card_ind], (clue_info in target_card[card_ind]))
            if clue in self.cards[card_ind]:
                kcard = self.known_cards[card_ind]
                if clue_type == 0:
                    self.known_cards[card_ind] = kcard[:1] + f"{clue_value}" + kcard[2:]
                elif clue_type == 1:
                    self.known_cards[card_ind] = kcard[:3] + f"{clue_value}" + kcard[4:]


# I_R_ 表示牌,当表示自己的牌是未知的时候使用 IURU
class GameController():
    def start_game(self, gameargs: GameArgs):
        # if not gameargs.random_start:
        #     if gameargs.start_card is None:
        #         print("ERROR: 没有设置开始牌型")
        #     elif len(gameargs.start_card) != gameargs.players * gameargs.players_card:
        #         print("ERROR: 并非所有玩家都有初始牌型")
        #     elif gameargs.allow_drawback:
        #         print("ERROR: 非随机对局不允许撤回AI的操作")

        # self.online_card_order = []
        self.game_history = []
        self.players_count = gameargs.players
        self.players_card_count = gameargs.players_card
        self.players = []
        self.AIplayes = gameargs.AIplayer
        self.AItokens = [[] for _ in range(self.players_count)]
        self.AImasks = [[] for _ in range(self.players_count)]
        self.AIturn = [1 for _ in range(self.players_count)]
        self.draw_check_value = random.randint(2, 7)
        # 目前默认所有玩法都是普通玩法

        self.allow_drawback = gameargs.allow_drawback
        # 是否是一把随机发牌的游戏(这说明只存在AI,并且整个游戏是完全自动的)
        self.ramdom_start = gameargs.random_start
        # 所有牌，发牌按照该顺序发牌
        self.all_cards = []
        self.discard_cards = []
        # 目前发到的牌的index
        self.current_card_index = 0

        self.game_actions = []
        self.AI_pred_cache = [[] for _ in range(self.players_count)]
        self.action_list_cache = None

        self.op_token = f"OP-{gameargs.variant}-P{self.players_count}"
        self.turn = 0
        self.clue = 8
        self.score = 0
        self.mistake = 0
        self.active_pid = 0
        self.round_p = 0
        self.round = 0
        # Irank是目前的花色的情况
        self.remain_round = self.players_count

        variant_one_card = ["Dark Null", "Dark Brown", "Cocoa Rainbow", "Gray", "Black", "Dark Rainbow", "Gray Pink",
                            "Dark Pink", "Dark Omni"]
        no_color_rule_variant = ["Null", "White", "Light Pink", "Dark Null", "Gray", "Gray Pink"]
        all_color_rule_variant = ["Muddy Rainbow", "Rainbow", "Omni", "Cocoa Rainbow", "Dark Rainbow", "Dark Omni"]
        no_rank_rule_variant = ["Null", "Brown", "Muddy Rainbow", "Dark Null", "Dark Brown", "Cocoa Rainbow"]
        all_rank_rule_variant = ["Light Pink", "Pink", "Omni", "Gray Pink", "Dark Pink", "Dark Omni"]

        self.variant_name = gameargs.variant
        self.last_one_card = False
        self.special_dict = SpecialGameArgs()

        # 游戏初始情况
        if "6 Suits" in self.variant_name:
            # 6张牌
            self.Irank = [0, 0, 0, 0, 0, 0]
            self.Hrank = [5, 5, 5, 5, 5, 5]
            index_amount = 6
            self.special_dict.last_special_card = 5
            self.total_card = 60
        elif "4 Suits" in self.variant_name:
            # 4张牌
            self.Irank = [0, 0, 0, 0]
            self.Hrank = [5, 5, 5, 5]
            index_amount = 4
            self.special_dict.last_special_card = 3
            self.total_card = 40
        else:
            # 5张牌
            self.Irank = [0, 0, 0, 0, 0]
            self.Hrank = [5, 5, 5, 5, 5]
            index_amount = 5
            self.special_dict.last_special_card = 4
            self.total_card = 50

        for vstr in variant_one_card:
            if vstr in self.variant_name:
                self.last_one_card = True
                self.total_card -= 5
                break
        for vstr in no_color_rule_variant:
            if vstr in self.variant_name:
                self.special_dict.no_color_rule = True
                break
        for vstr in all_color_rule_variant:
            if vstr in self.variant_name:
                self.special_dict.all_color_rule = True
                break
        for vstr in no_rank_rule_variant:
            if vstr in self.variant_name:
                self.special_dict.no_rank_rule = True
                break
        for vstr in all_rank_rule_variant:
            if vstr in self.variant_name:
                self.special_dict.all_rank_rule = True
                break

        self.options_token_list = [f"Players-{self.players_count}", f"Suits-{index_amount}"]
        last_pos_color = self.variant_name
        if last_pos_color != "No Variant" and last_pos_color != "6 Suits" and last_pos_color != "4 Suits":
            last_pos_color = last_pos_color.replace("(5 Suits)", "")
            last_pos_color = last_pos_color.replace("(6 Suits)", "")
            last_pos_color = last_pos_color.strip()
            self.options_token_list.append(f"Special-I{self.special_dict.last_special_card}-{last_pos_color}")

        for pid in range(self.players_count):
            self.players.append(GamePlayer(pid, self))

    def get_histroy_tokens(self, current_index):
        token_list = []
        my_pid = self.active_pid
        #print("my_pid ", my_pid)
        for index in range(current_index + 1):
            history_dict = self.game_history[index]
            action = history_dict["action"]
            active_pid = history_dict["active_pid"]
            action_cause = history_dict["action_cause"]
            if active_pid == my_pid:
                #轮到本玩家操作
                cards = history_dict["cards"]
                kcards = history_dict["kcards"]
                suits = len(history_dict["Hrank"])
                varient = history_dict["varient"]
                #所有人的卡(PRN->PR0)
                for rpid in range(self.players_count - 1, -1, -1):
                    pid = active_pid + rpid
                    if pid >= self.players_count:
                        pid -= self.players_count
                    #print("pid,rpid", pid, rpid)
                    token = f"light-PR{rpid}"
                    token_list.append(token)
                    for i in range(len(cards[pid])):
                        lcard = cards[pid][i]
                        kcard = kcards[pid][i]
                        if rpid == 0:
                            token = f"light-myself-{kcard}"
                        else:
                            token = f"light-{lcard}-{kcard}"
                        token_list.append(token)
                #对局信息
                #"Players-2", "Suits-6", "Special-I5-Rainbow", "myturn-1", "clues-8"
                token_list.append(f"Players-{self.players_count}")
                token_list.append(f"Suits-{suits}")
                if varient != "No Variant" and varient != "6 Suits" and varient != "4 Suits":
                    token_list.append(varient)
                token_list.append(f'myturn-{history_dict["myturn"]}')
                token_list.append(f'clues-{history_dict["clue"]}')
                #已经行动的步骤要添加到token中
                if index < current_index:
                    token_list.append(action["token"])
                    if action_cause is not None:
                        token_list.append(action_cause)
            else:
                #其他玩家操作
                raction_token = self.get_action_token(action, my_pid)
                token_list.append(raction_token)
                #有一张牌被弃或打出了
                if action_cause is not None:
                    token_list.append(action_cause)
        return token_list

    def set_current_history(self, index, topk):
        history_dict = self.game_history[index]
        self.Irank = history_dict["Irank"]
        self.Hrank = history_dict["Hrank"]
        self.score = sum(self.Irank)
        for i in range(self.players_count):
            self.players[i].cards = history_dict["cards"][i]
            self.players[i].known_cards = history_dict["kcards"][i]
        self.clue = history_dict["clue"]
        self.active_pid = history_dict["active_pid"]
        action = history_dict["action"]
        input_token_list = self.get_histroy_tokens(index)

        # print("===================")
        # print(self.game_history[index]["AItoken"])
        # print(input_token_list)
        # print("===================")

        action_ids, action_probs = generate_answer(self.model, input_token_list, self.action_dict_toid, self.device, topk)
        action_list = []
        detail_action_list = []
        sum_prob = sum(action_probs)
        for i in range(topk):
            action_token = self.output_action_dict_toact[action_ids[i]]
            action_list.append({"token": action_token, "probs": (action_probs[i] / sum_prob).item()})
            action_info = self.get_action(action_token, self.active_pid)
            detail_action_list.append(action_info)
        return action, action_list, detail_action_list

    def get_current_card(self):
        current_card = self.total_card - self.score - len(self.discard_cards) - self.players_count * self.players_card_count
        if current_card <= 0:
            return 0
        return current_card

    def add_card_deck(self, card):
        self.all_cards.append(card)

    def __init__(self, model_data=None, game_config=None):
        if model_data is None:
            self.model, self.action_dict_toact, self.action_dict_toid, self.output_action_dict_toact, self.output_action_dict_toid, self.device = load_model()
        else:
            self.model = model_data[0]
            self.action_dict_toact = model_data[1]
            self.action_dict_toid = model_data[2]
            self.output_action_dict_toact = model_data[3]
            self.output_action_dict_toid = model_data[4]
            self.device = model_data[5]

    def parse_card(self, card):
        if card[1] == "_":
            index = 9
        else:
            index = int(card[1])
        if card[3] == "_":
            rank = 9
        else:
            rank = int(card[3])
        return index, rank

    def update_AI_token(self, active_pid):
        # 补充所有的玩家目前的手牌情况
        light_cards = [[] for _ in range(self.players_count)]
        # for iindex in range(len(self.Irank)):
        #     irank_str = f"irank-I{iindex}R{self.Irank[iindex]}"
        #     #print(irank_str)
        #     self.AItokens[active_pid].append(irank_str)
        # self.AItokens[active_pid].append(f"score-{self.score}")
        for pid in range(self.players_count):
            rpid = pid - active_pid
            if rpid < 0:
                rpid += self.players_count
            player = self.players[pid]
            if rpid == 0:
                light_cards[rpid] = player.get_light_card_myself()
            else:
                light_cards[rpid] = player.get_light_card(rpid)

        for i in range(len(light_cards) - 1, -1, -1):
            self.AItokens[active_pid].extend(light_cards[i])
            self.AImasks[active_pid].extend([0] * len(light_cards[i]))

        # 给AI们更新游戏状态token
        for options_token in self.options_token_list:
            self.AItokens[active_pid].append(options_token)
            self.AImasks[active_pid].append(0)
        # 其余信息
        self.AItokens[active_pid].append(f"myturn-{self.AIturn[active_pid]}")
        self.AImasks[active_pid].append(0)
        self.AItokens[active_pid].append(f"clues-{self.clue}")
        self.AImasks[active_pid].append(0)

    def call_AI_predict(self, active_pid, topk):
        # AI行动(更新token)
        self.update_AI_token(active_pid)
        action_ids, action_probs = generate_answer(self.model, self.AItokens[active_pid], self.action_dict_toid, self.device, topk)
        action_list = []
        self.AI_pred_cache[active_pid].append([])
        sum_prob = sum(action_probs)
        for i in range(topk):
            action_token = self.output_action_dict_toact[action_ids[i]]
            action_list.append({"token": action_token, "probs": (action_probs[i] / sum_prob).item()})
            action_info = self.get_action(action_token, active_pid)
            self.AI_pred_cache[active_pid][self.round].append(action_info)
        return action_list, self.AI_pred_cache[active_pid][self.round]

    def get_action(self, action_token, my_pid):
        action = None
        if action_token.startswith("clue"):
            clue = action_token[-2:]
            to_rpid = int(action_token[-4])
            to_pid = to_rpid + my_pid
            if to_pid >= self.players_count:
                to_pid -= self.players_count
            if clue[0] == "I":
                clue_type = 0
            else:
                clue_type = 1
            clue_value = int(clue[1])
            action = {
                "str": f"提示P{to_pid}:{clue}",
                "type": "clue",
                "from": my_pid,
                "to": to_pid,
                "clue_type": clue_type,
                "clue_value": clue_value,
                "clue": clue,
            }
        elif action_token.startswith("play"):
            postion = action_token[-1]
            action = {
                "str": f"出牌:第{len(self.players[my_pid].cards) - int(postion)}张牌",
                "type": "play",
                "pid": my_pid,
                "pos": int(postion),
            }
        elif action_token.startswith("discard"):
            postion = action_token[-1]
            action = {
                "str": f"弃牌:第{len(self.players[my_pid].cards) - int(postion)}张牌",
                "type": "discard",
                "pid": my_pid,
                "pos": int(postion),
            }
        return action

    def get_rpid(self, input_pid, my_pid):
        rpid = input_pid - my_pid
        if rpid < 0:
            rpid += self.players_count
        return rpid

    def get_action_token(self, action, my_pid):
        try:
            action_token = ""
            action_type = action["type"]
            if action_type == "clue":
                from_pid = action["from"]
                to_pid = action["to"]
                clue = action["clue"]
                from_rpid = self.get_rpid(from_pid, my_pid)
                to_rpid = self.get_rpid(to_pid, my_pid)
                if from_rpid == 0:
                    action_token = f"clue-myself->PRT{to_rpid}-{clue}"
                elif to_rpid == 0:
                    action_token = f"clue-PRF{from_rpid}->myself-{clue}"
                else:
                    action_token = f"clue-PRF{from_rpid}->PRT{to_rpid}-{clue}"
            elif action_type == "play":
                pid = action["pid"]
                pos = action["pos"]
                rpid = self.get_rpid(pid, my_pid)
                if rpid == 0:
                    action_token = f"play-myself-POS{pos}"
                else:
                    action_token = f"play-PR{rpid}-POS{pos}"
            elif action_type == "discard":
                pid = action["pid"]
                pos = action["pos"]
                rpid = self.get_rpid(pid, my_pid)
                if rpid == 0:
                    action_token = f"discard-myself-POS{pos}"
                else:
                    action_token = f"discard-PR{rpid}-POS{pos}"
        except Exception as e:
            print(f'Error reading history: {e}')
            traceback.print_exc()
            action_token = "NULL"
        return action_token

    def draw_card(self, to_pid):
        if self.ramdom_start:
            self.draw_next_card(to_pid)
        else:
            self.draw_next_card(to_pid)

    def draw_spec_card(self, card, to_pid):
        self.players[to_pid].gain_card(card)

    def draw_next_card(self, to_pid):
        if self.current_card_index == len(self.all_cards):
            # 没牌了，不发了
            return
        card = self.all_cards[self.current_card_index]
        self.draw_spec_card(card, to_pid)
        self.current_card_index += 1

    ###
    # 以下都是用来和在线游戏对接的接口
    ###

    def online_handle_draw(self, action_data):
        playerIndex = action_data["playerIndex"]
        order = action_data["order"]
        index = action_data["suitIndex"]
        rank = action_data["rank"]
        if index == -1:
            index = 9
        if rank == -1:
            rank = 9
        card = f"I{index}R{rank}"
        self.players[playerIndex].gain_card(card, order)

    def online_handle_play(self, action_data):
        pid = action_data["playerIndex"]
        cindex = action_data["suitIndex"]
        crank = action_data["rank"]
        order = action_data["order"]
        card = f"I{cindex}R{crank}"
        player = self.players[pid]
        pos = player.online_order.index(order)

        #判断是AI预测的第几个操作
        ai_rank = "N"
        if self.round < len(self.AI_pred_cache[pid]):
            if len(self.AI_pred_cache[pid][self.round]) > 0:
                for i in range(len(self.AI_pred_cache[pid][self.round])):
                    ai_pred = self.AI_pred_cache[pid][self.round][i]
                    if ai_pred["type"] == "play" and ai_pred["pos"] == pos:
                        ai_rank = i + 1
                        break

        action_str = f"P{pid}-出牌:第{len(self.players[pid].cards) - int(pos)}张牌[{ai_rank}]"
        player.remove_card_at(pos)
        if self.Irank[cindex] + 1 == crank:
            # 成功打牌
            self.score += 1
            # 打出第五张牌多一个提示
            if crank == 5 and self.clue < 8:
                self.clue += 1
            self.Irank[cindex] += 1
        else:
            # 打牌失败
            self.discard_cards.append(card)

        # 给AI们更新token
        for aipid in self.AIplayes:
            if aipid == pid:
                self.AItokens[aipid].append(f"play-myself-POS{pos}")
                self.AImasks[aipid].append(1)
            else:
                rpid = pid - aipid
                if rpid < 0:
                    rpid += self.players_count
                self.AItokens[aipid].append(f"play-PR{rpid}-POS{pos}")
                self.AImasks[aipid].append(0)
            self.AItokens[aipid].append(f"played-{card}")
            self.AImasks[aipid].append(0)
        return action_str

    def online_handle_discard(self, action_data):
        pid = action_data["playerIndex"]
        cindex = action_data["suitIndex"]
        crank = action_data["rank"]
        order = action_data["order"]
        failed = action_data["failed"]
        player = self.players[pid]
        card = f"I{cindex}R{crank}"
        pos = player.online_order.index(order)

        # 判断是AI预测的第几个操作
        ai_rank = "N"
        if self.round < len(self.AI_pred_cache[pid]):
            if len(self.AI_pred_cache[pid][self.round]) > 0:
                for i in range(len(self.AI_pred_cache[pid][self.round])):
                    ai_pred = self.AI_pred_cache[pid][self.round][i]
                    if failed:
                        if ai_pred["type"] == "play" and ai_pred["pos"] == pos:
                            ai_rank = i + 1
                            break
                    else:
                        if ai_pred["type"] == "discard" and ai_pred["pos"] == pos:
                            ai_rank = i + 1
                            break

        if failed:
            action_str = f"P{pid}-出牌失败:第{len(self.players[pid].cards) - int(pos)}张牌[{ai_rank}]"
        else:
            action_str = f"P{pid}-弃牌:第{len(self.players[pid].cards) - int(pos)}张牌[{ai_rank}]"
        damounts = self.discard_cards.count(card)
        if self.Irank[cindex] < crank:
            if crank == 1 and damounts == 2:
                self.Hrank[cindex] = min(crank - 1, self.Hrank[cindex])
            elif crank < 5 and damounts == 1:
                self.Hrank[cindex] = min(crank - 1, self.Hrank[cindex])
            elif crank == 5:
                self.Hrank[cindex] = min(crank - 1, self.Hrank[cindex])

        player.remove_card_at(pos)
        self.discard_cards.append(card)
        # 多一个提示(实际上打牌失败会被算成弃牌)
        if failed:
            self.mistake += 1
        if self.clue < 8 and not failed:
            self.clue += 1

        for aipid in self.AIplayes:
            if aipid == pid:
                if failed:
                    #失败
                    self.AItokens[aipid].append(f"play-myself-POS{pos}")
                else:
                    self.AItokens[aipid].append(f"discard-myself-POS{pos}")
                self.AImasks[aipid].append(1)
            else:
                rpid = pid - aipid
                if rpid < 0:
                    rpid += self.players_count
                if failed:
                    #失败
                    self.AItokens[aipid].append(f"play-PR{rpid}-POS{pos}")
                else:
                    self.AItokens[aipid].append(f"discard-PR{rpid}-POS{pos}")
                self.AImasks[aipid].append(0)
            self.AItokens[aipid].append(f"lossed-{card}")
            self.AImasks[aipid].append(0)
        return action_str

    def online_handle_clue(self, action_data):
        from_pid = action_data["giver"]
        to_pid = action_data["target"]
        clue_type = action_data['clue']["type"]
        clue_value = action_data['clue']["value"]
        order_list = action_data['list']
        player = self.players[to_pid]
        for order in order_list:
            pos = player.online_order.index(order)
            kcard = player.known_cards[pos]
            card = player.cards[pos]
            card_type = int(card[1])
            kcard_type = kcard[1]
            kcard_rank = kcard[3]
            if self.special_dict.last_special_card == card_type:
                # 最后一张牌,可能有特殊规则限制
                if self.special_dict.all_color_rule and kcard_type != "_" and clue_type == 0:
                    # 颜色提示
                    if int(kcard_type) == self.special_dict.last_special_card:
                        # 已经明示,不再额外提醒
                        continue
                    if int(kcard_type) != clue_value:
                        # 不同的颜色提示（彰显特殊牌）
                        player.known_cards[pos] = kcard[:1] + f"{self.special_dict.last_special_card}" + kcard[2:]
                        # print(target_known_card[index_of_card], variantName)
                        continue
                if self.special_dict.all_rank_rule and kcard_rank != "_" and clue_type == 1:
                    # 数字提示
                    if kcard_type == f"{self.special_dict.last_special_card}":
                        # 已经明示,不再额外提醒(只提示数字)
                        player.known_cards[pos] = kcard[:3] + f"{clue_value}" + kcard[4:]
                        continue
                    if int(kcard_rank) != clue_value:
                        # 不同的数字提示（彰显特殊牌）
                        player.known_cards[pos] = f"I{self.special_dict.last_special_card}R{clue_value}"
                        # print(target_known_card[index_of_card], variantName)
                        continue
            if clue_type == 0:
                player.known_cards[pos] = kcard[:1] + f"{clue_value}" + kcard[2:]
            elif clue_type == 1:
                player.known_cards[pos] = kcard[:3] + f"{clue_value}" + kcard[4:]
        self.clue -= 1

        clue_info = ""
        if clue_type == 0:
            clue_info = f"I{clue_value}"
        elif clue_type == 1:
            clue_info = f"R{clue_value}"

        # 判断是AI预测的第几个操作
        ai_rank = "N"
        if self.round < len(self.AI_pred_cache[from_pid]):
            if len(self.AI_pred_cache[from_pid][self.round]) > 0:
                for i in range(len(self.AI_pred_cache[from_pid][self.round])):
                    ai_pred = self.AI_pred_cache[from_pid][self.round][i]
                    if ai_pred["type"] == "clue" and ai_pred["to"] == to_pid and ai_pred["clue"] == clue_info:
                        ai_rank = i + 1
                        break

        action_str = f"P{from_pid}提示P{to_pid}:{clue_info}[{ai_rank}]"

        # 给AI们更新token
        for aipid in self.AIplayes:
            from_rpid = from_pid - aipid
            if from_rpid < 0:
                from_rpid += self.players_count
            to_rpid = to_pid - aipid
            if to_rpid < 0:
                to_rpid += self.players_count
            clue_token = f"clue-PRF{from_rpid}->PRT{to_rpid}-{clue_info}"
            clue_token = clue_token.replace("PRF0", "myself")
            clue_token = clue_token.replace("PRT0", "myself")
            self.AItokens[aipid].append(clue_token)
            if from_rpid == 0:
                self.AImasks[aipid].append(1)
            else:
                self.AImasks[aipid].append(0)
        return action_str

    def online_handle_status(self, action_data):
        self.round_p += 1
        self.round = math.floor(self.round_p / self.players_count)
        clues = action_data["clues"]
        score = action_data["score"]
        maxScore = action_data["maxScore"]
        if clues != self.clue or score != self.score or maxScore != sum(self.Hrank):
            print(f"ERROR:C {clues}={self.clue} |S {score}={self.score} |MS {maxScore}={sum(self.Hrank)}")
        # for aipid in self.AIplayes:
        #     self.AItokens[aipid].append(f"status-{self.clue}")
        #     self.AImasks[aipid].append(0)
