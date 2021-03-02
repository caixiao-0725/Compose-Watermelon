import torch
import torch.nn as nn
import torch.optim as optim
import random
import math
import numpy as np
from memory import ReplayBuffer
# from model import WaterNet
from torchvision.models import resnet50


class DQN:
    def __init__(self, n_actions = 100,gamma=0.99, epsilon_start=0.95, epsilon_end=0.05, epsilon_decay=500,
                 memory_capacity=1000, policy_lr=0.01, batch_size=64, device="cuda",path="D:/unity2017/water/ai/saved_model/checkpoint1.pth",pretrained = False):
        self.path = path
        self.device = device  # 设备，cpu或gpu等
        self.gamma = gamma  # 奖励的折扣因子
        self.n_actions = n_actions
        # e-greedy策略相关参数
        self.actions_count = 0  # 用于epsilon的衰减计数
        self.epsilon = 0
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.policy_net = resnet50()
        num_ftrs = self.policy_net.fc.in_features
        self.policy_net.fc = nn.Linear(num_ftrs, self.n_actions)
        self.policy_net.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.policy_net.to(self.device)
        if pretrained:
            self.policy_net.load_state_dict(torch.load(self.path))
        self.target_net = resnet50()
        self.target_net.conv1 = nn.Conv2d(1, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.target_net.fc = nn.Linear(num_ftrs, self.n_actions)
        self.target_net.to(self.device)
        # target_net的初始模型参数完全复制policy_net
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()  # 不启用 BatchNormalization 和 Dropout
        # 可查parameters()与state_dict()的区别，前者require_grad=True
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=policy_lr)
        self.loss = 0
        self.memory = ReplayBuffer(memory_capacity)
        self.pretrained =pretrained

    def choose_action(self, state, train=True):
        '''选择动作
        '''
        if train:
            self.epsilon = self.epsilon_end + (self.epsilon_start - self.epsilon_end) * math.exp(-1. * self.actions_count / self.epsilon_decay)
            self.actions_count += 1
            #if self.pretrained:
            #   self.epsilon = self.epsilon_end
            if random.random() > self.epsilon:
                with torch.no_grad():
                    # 先转为张量便于丢给神经网络,state元素数据原本为float64
                    # 注意state=torch.tensor(state).unsqueeze(0)跟state=torch.tensor([state])等价
                    # 如tensor([[-0.0798, -0.0079]], grad_fn=<AddmmBackward>)
                    state = state.unsqueeze(0).to(self.device)
                    q_value = self.policy_net(state)
                    action = q_value.max(1)[1].item()
            else:
                action = random.randint(0,99)
            return action
        else:
            with torch.no_grad():  # 取消保存梯度
                # 先转为张量便于丢给神经网络,state元素数据原本为float64
                # 注意state=torch.tensor(state).unsqueeze(0)跟state=torch.tensor([state])等价
                state = torch.tensor(
                    state, device='cpu',
                    dtype=torch.float32)  # 如tensor([[-0.0798, -0.0079]], grad_fn=<AddmmBackward>)
                q_value = self.target_net(state)
                action = q_value.max(1)[1].item()
            return action

    def update(self):

        if len(self.memory) < self.batch_size:
            return
        # 从memory中随机采样transition
        state_batch_, action_batch, reward_batch, next_state_batch_, done_batch = self.memory.sample(self.batch_size)
        state_batch = torch.ones((self.batch_size,1,150,6),device=self.device, dtype=torch.float)
        for i in range(self.batch_size):
            state_batch[i]=state_batch_[i]
        next_state_batch = torch.ones((self.batch_size,1,150,6),device=self.device, dtype=torch.float)
        for i in range(self.batch_size):
            next_state_batch[i]=next_state_batch_[i]
        '''转为张量
        例如tensor([[-4.5543e-02, -2.3910e-01,  1.8344e-02,  2.3158e-01],...,[-1.8615e-02, -2.3921e-01, -1.1791e-02,  2.3400e-01]])'''
        # state_batch = torch.tensor(state_batch, device=self.device,dtype=torch.float)
        action_batch = torch.tensor(action_batch, device=self.device).unsqueeze(1)  # 例如tensor([[1],...,[0]])
        reward_batch = torch.tensor(
            reward_batch, device=self.device, dtype=torch.float)  # tensor([1., 1.,...,1])
        # next_state_batch = torch.tensor(
        #     next_state_batch, device=self.device, dtype=torch.float)
        done_batch = torch.tensor(np.float32(
            done_batch), device=self.device).unsqueeze(1)  # 将bool转为float然后转为张量

        '''计算当前(s_t,a)对应的Q(s_t, a)'''
        '''torch.gather:对于a=torch.Tensor([[1,2],[3,4]]),那么a.gather(1,torch.Tensor([[0],[1]]))=torch.Tensor([[1],[3]])'''
        q_values = self.policy_net(state_batch).gather(dim=1, index=action_batch)  # 等价于self.forward
        # 计算所有next states的V(s_{t+1})，即通过target_net中选取reward最大的对应states
        next_state_values = self.target_net(next_state_batch).max(1)[0].detach()  # 比如tensor([ 0.0060, -0.0171,...,])
        # 计算 expected_q_value
        # 对于终止状态，此时done_batch[0]=1, 对应的expected_q_value等于reward
        expected_q_values = reward_batch + self.gamma * \
                            next_state_values * (1 - done_batch[0])
        # self.loss = F.smooth_l1_loss(q_values,expected_q_values.unsqueeze(1)) # 计算 Huber loss
        self.loss = nn.MSELoss()(q_values, expected_q_values.unsqueeze(1))  # 计算 均方误差loss
        # 优化模型
        self.optimizer.zero_grad()  # zero_grad清除上一步所有旧的gradients from the last step
        # loss.backward()使用backpropagation计算loss相对于所有parameters(需要gradients)的微分
        self.loss.backward()
        for param in self.policy_net.parameters():  # clip防止梯度爆炸
            param.grad.data.clamp_(-1, 1)

        self.optimizer.step()  # 更新模型

    def save_model(self, path):
        torch.save(self.target_net.state_dict(), path)

    def load_model(self, path):
        self.target_net.load_state_dict(torch.load(path))