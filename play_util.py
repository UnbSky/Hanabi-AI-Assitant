
import sys
type = sys.getfilesystemencoding()
import json
import torch
from net.model import ModelArgs, Transformer
import numpy as np

def load_model(model_name=None):
    #device = 'cuda' if torch.cuda.is_available() else 'cpu'  # examples: 'cpu', 'cuda', 'cuda:0', 'cuda:1', etc.
    device = 'cpu'

    acition_dict_toid = {}
    if model_name is None:
        dict_path = 'dict.json'
    else:
        dict_path = f'{model_name}/dict.json'
    with open(dict_path, 'r', encoding='utf-8') as file:
        acition_dict = json.load(file)
        acition_dict = ["<pad>"] + acition_dict
        ind = 0
        for action in acition_dict:
            acition_dict_toid[action] = ind
            #print(action, ind)
            ind += 1
        n_vacabs = len(acition_dict)
    output_acition_dict_toid = {}
    if model_name is None:
        output_dict_path = 'output_dict.json'
    else:
        output_dict_path = f'{model_name}/output_dict.json'
    with open(output_dict_path, 'r', encoding='utf-8') as file:
        output_acition_dict = json.load(file)
        output_acition_dict = ["<pad>"] + output_acition_dict
        ind = 0
        for action in output_acition_dict:
            output_acition_dict_toid[action] = ind
            #print(action, ind)
            ind += 1
        n_vacabs_out = len(output_acition_dict)

    if model_name is None:
        max_seq_len = 900
        dim = 384
        n_layers = 8
        n_heads = 8
        multiple_of = 32
        dropout = 0.0
        model_args = dict(
            dim=dim,
            n_layers=n_layers,
            n_heads=n_heads,
            n_kv_heads=n_heads,
            vocab_size=n_vacabs,
            output_vocab_size=n_vacabs_out,
            multiple_of=multiple_of,
            max_seq_len=max_seq_len,
            dropout=dropout,
        )  # s
    else:
        with open(f'{model_name}/config.json', 'r') as json_file:
            model_config = json.load(json_file)
            model_args = model_config["model_args"]

    seed = 1337
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cuda.matmul.allow_tf32 = True  # allow tf32 on matmul
    torch.backends.cudnn.allow_tf32 = True  # allow tf32 on cudnn

    # init from a model saved in a specific directory
    if model_name is None:
        ckpt_path = 'best_valid.pth'
    else:
        ckpt_path = f'{model_name}/model.pth'
    state_dict = torch.load(ckpt_path, map_location=device)
    gptconf = ModelArgs(**model_args)
    model = Transformer(gptconf)
    unwanted_prefix = '_orig_mod.'
    for k, v in list(state_dict.items()):
        if k.startswith(unwanted_prefix):
            state_dict[k[len(unwanted_prefix):]] = state_dict.pop(k)
    model.load_state_dict(state_dict, strict=False)
    model.eval()
    model.to(device)
    return model, acition_dict, acition_dict_toid, output_acition_dict, output_acition_dict_toid, device

def generate_answer(model, input_actions, acition_dict_toid, device, topk):
    input_id = []
    for action in input_actions:
        if len(action) < 1:
            continue
        if any(char.isalpha() for char in action):
            action = action.strip()
            if action not in acition_dict_toid:
                print(f"NULL[{action}]")
                return f"NULL[{action}]"
            input_id.append(acition_dict_toid[action])
    #print(input_id)
    input_id = np.array([input_id])
    input_id = torch.from_numpy(input_id)
    input_id = input_id.to(device)
    idx, probs = model.play_topk(input_id, topk)
    return idx, probs

def generate_answer_ahead(model, input_actions, input_pos, acition_dict_toid, output_action_dict_toact, device, topk, ahead_step, ahead_p):
    input_id = []
    for action in input_actions:
        if len(action) < 1:
            continue
        if any(char.isalpha() for char in action):
            action = action.replace("light-myself","light_myself")
            action = action.strip()
            if action not in acition_dict_toid:
                #print(f"NULL[{action}]")
                return f"NULL[{action}]"
            input_id.append(acition_dict_toid[action])
    input_id = np.array([input_id])
    input_id = torch.from_numpy(input_id)
    input_id = input_id.to(device)
    idx, probs = model.play_topk(input_id, topk)
    max_prob = 0
    return_idx = None
    ind = 0
    for ava_id in idx:
        input_next_id = input_id
        current_prob = probs[ind]
        current_action = output_action_dict_toact[ava_id]
        # current_action = current_action.replace("light-myself","light_myself")
        next_id = acition_dict_toid[current_action]
        next_id = torch.tensor(np.array([[next_id]])).to(device)
        # print(current_action)
        ind += 1
        for step in range(ahead_step):
            input_next_id = torch.cat((input_next_id, next_id), dim=1)
            next_id, prob = model.play_topk(input_next_id, 1)
            next_action = output_action_dict_toact[next_id]
            # print(next_action)
            next_id = acition_dict_toid[next_action]
            next_id = torch.tensor(np.array([[next_id]])).to(device)
            current_prob += prob * pow(ahead_p, step + 1)
        if current_prob > max_prob:
            max_prob = current_prob
            return_idx = ava_id
        # print(ava_id, current_prob)
    return return_idx, max_prob

