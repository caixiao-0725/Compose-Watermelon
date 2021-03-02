import socket
from clean import data_clean
from agent import DQN
import torch
import time
import os


def save_model(agent,model_path):
    if not os.path.exists(model_path): # 检测是否存在文件夹
        os.mkdir(model_path)
    agent.save_model(model_path+'checkpoint1.pth')

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
SAVED_MODEL_PATH = 'D:/unity2017/water/ai/saved_model/'


# 构建Socket实例、设置端口号和监听队列大小
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.bind(('127.0.0.1', 50213))
listener.listen(5)
print('Waiting for connect...')

while True:
    client_executor, addr = listener.accept()
    if addr!=None:
        break

print('Accept new connection from %s:%s...' % addr)

agent = DQN(pretrained=True)
state = torch.zeros((150, 6),device=device,dtype=torch.float)
state[0][5] = 0.26
state[0][1] = 4.75
state = state.unsqueeze(0)
reward = 0
for i in range(6005):

    if i ==0:
        action = 50
        #action = torch.zeros((1),device=device,dtype=torch.float,requires_grad=False)
    else:
        action = agent.choose_action(state)
    msg = client_executor.recv(16384).decode('utf-8')
    client_executor.send(bytes(str(action / 10 - 5).encode('utf-8')))

    next_state, new_reward, done = data_clean(msg)
    add_reward = new_reward - reward
    reward = new_reward
    agent.memory.push(state, action, add_reward, next_state, done)
    state = next_state
    start = time.time()
    agent.update()  # 每步更新网络
    end = time.time()
    if(i%200==199):
        save_model(agent,model_path=SAVED_MODEL_PATH)
        print("save",i)
    print(str(action/10-5),end-start)





