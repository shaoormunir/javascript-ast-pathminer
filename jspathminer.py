import json
import esprima
from tqdm import tqdm
import pickle
import glob


class DocumentContext:
    def __init__(self):
        self.start_token_ids = []
        self.end_token_ids = []
        self.path_ids = []
        self.document_path = ""
        self.document_label = ""
        self.document_id = 0

    def print(self):
        print(f"#{self.document_id}")
        print(f"label:{self.document_label}")
        print(f"class:{self.document_path}")
        print("paths:")
        for start, end, path in zip(self.start_token_ids, self.end_token_ids, self.path_ids):
            print(f"{start}\t{end}\t{path}")


class PathContext:
    def __init__(self, start_token):
        self.start_token = start_token
        self.path = ""
        self.end_token = ""
        self.complete_context = False

    def print(self):
        print(f"{self.start_token} | {self.path} | {self.end_token}")


def get_data_type_expression(data, expression):
    symbol = ""
    if expression == "BinaryExpression":
        if data['operator'] == '+':
        symbol = ":SUM"
        if data['operator'] == '-':
        symbol = ":SUB"
        if data['operator'] == '*':
        symbol = ":MUL"
        if data['operator'] == '/':
        symbol = ":DIV"
        if data['operator'] == '%':
        symbol = ":MOD"

    if expression == "LogicalExpression":
        symbol = ""
        if data['operator'] == '||':
        symbol = ":OR"
        if data['operator'] == '&&':
        symbol = ":AND"

    return expression+symbol


def get_new_path_context(start_token):
    path_context = PathContext(start_token)
    return path_context


def recursive_traverse(data, contexts, path, up):
    if isinstance(data, dict):
        if len(path) == 0 and data.get('type', '') == 'Identifier':
            contexts.append(get_new_path_context(data.get('name', '')))
            path = f"{data.get('type', '')} ↑"
            return contexts, path, True

        if len(path) != 0 and data.get('type', '') == 'Identifier':
            if (contexts[len(contexts)-1].complete_context):
                contexts.append(get_new_path_context(
                    contexts[len(contexts)-1].start_token))
            contexts[len(contexts)-1].end_token = data.get('name', '')
            path += f" {data.get('type', '')}"
            # print(path)
            contexts[len(contexts)-1].path = path
            contexts[len(contexts)-1].complete_context = True
            contexts.append(get_new_path_context(data.get('name', '')))
            path = f"{data.get('type', '')} ↑"
            return contexts, path, False

        if len(path) != 0 and data.get('type', '') == 'Literal':
            if (contexts[len(contexts)-1].complete_context):
                contexts.append(get_new_path_context(
                    contexts[len(contexts)-1].start_token))
            contexts[len(contexts)-1].end_token = data.get('value', '')
            path += f" {data.get('type', '')}"
            contexts[len(contexts)-1].path = path
            contexts[len(contexts)-1].complete_context = True
            # print(path)
            return contexts, "", False
        for key, value in data.items():
            temp_path = path
            contexts, path, up = recursive_traverse(value, contexts, path, up)

            if (len(path) != 0) and (temp_path != path):
                if up:
                    path += f" {get_data_type_expression(data, data.get('type', ''))} ↑"
                else:
                    path += f" {get_data_type_expression(data, data.get('type', ''))} ↓"

    elif isinstance(data, list):
        temp = ""
        for item in data:
            contexts, temp, up = recursive_traverse(item, contexts, path, up)
    return contexts, path, up


class PathMiner:
    def __init__(self, folder_path, output_path, checkpoint_after=200):
        self.folder_path = folder_path
        self.output_path = output_path
        self.checkpoint_after = checkpoint_after

    def mine_paths(self):
        doc_contexts = []
        path_idx = {}
        terminal_idx = {}
        files = glob.glob(self.folder_path, ".js")
        for js_file in tqdm(files):

            # for cat in tqdm(file_labels):
            # cat_files = file_labels[cat]
            # for cat_file in tqdm(cat_files):
            # file_path = data_dir + cat_file
            # methods.append(file_path + " " + cat)
        try:
            with open(js_file) as f:
                data = f.read()

                json_text = json.dumps(esprima.parseScript(data).toDict())
                json_data = json.loads(json_text)

                contexts, path, up = recursive_traverse(
                    json_data, [], "", False)

                doc_context = DocumentContext()
                doc_context.document_class = file_path
                doc_context.document_label = cat

                doc_context.document_id = len(doc_contexts)

                for context in contexts:
                    if not (isinstance(context.end_token, dict) or isinstance(context.start_token, dict) or isinstance(context.path, dict)):
                    if context.start_token not in terminal_idx:
                        terminal_idx[context.start_token] = len(terminal_idx)
                    if context.end_token not in terminal_idx:
                        terminal_idx[context.end_token] = len(terminal_idx)
                    if context.path not in path_idx:
                        path_idx[context.path] = len(path_idx)

                    doc_context.start_token_ids.append(
                        terminal_idx[context.start_token])
                    doc_context.end_token_ids.append(
                        terminal_idx[context.end_token])
                    doc_context.path_ids.append(path_idx[context.path])
                doc_contexts.append(doc_context)
                drive_path = "drive/My Drive/script-detector/model-checkpoints/"
                except IOError:
                print(f"Cannot open file : {file_path}")
                except Exception as e:
                print(f"Error in file: {file_path} due to {e}")
            with open(drive_path+"doc_contexts_checkpoint_" + cat+".pkl", "wb") as f:
                pickle.dump(doc_contexts, f)
            with open(drive_path+"terminal_idx_checkpoint_"+cat+".pkl", "wb") as f:
                pickle.dump(terminal_idx, f)
            with open(drive_path+"path_idx_checkpoint_"+cat+".pkl", "wb") as f:
                pickle.dump(path_idx, f)