import torch
import torch.nn as nn
import torch.optim as optim
from transformers import AutoModelForCausalLM, AutoTokenizer
from typing import List, Tuple
import numpy as np
from app.core.config import settings

class RLModel:
    def __init__(self):
        self.device = torch.device(settings.DEVICE if torch.cuda.is_available() else "cpu")
        self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
        self.model = AutoModelForCausalLM.from_pretrained(settings.MODEL_NAME).to(self.device)
        
        # Initialize reward model (simple feed-forward network)
        self.reward_model = nn.Sequential(
            nn.Linear(self.model.config.hidden_size, 512),
            nn.ReLU(),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Linear(128, 1)
        ).to(self.device)
        
        self.optimizer = optim.AdamW(list(self.model.parameters()) + list(self.reward_model.parameters()), lr=1e-5)
    
    def compute_reward(self, response_embedding: torch.Tensor, feedback: int) -> float:
        """Compute reward based on user feedback and response embedding."""
        predicted_reward = self.reward_model(response_embedding)
        actual_reward = torch.tensor([[feedback]], dtype=torch.float32).to(self.device)
        
        # Update reward model
        loss = nn.MSELoss()(predicted_reward, actual_reward)
        loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
        
        return feedback
    
    def update_policy(self, context: str, response: str, reward: float):
        """Update the language model policy using the computed reward."""
        # Tokenize input
        inputs = self.tokenizer(context + response, return_tensors="pt").to(self.device)
        
        # Get model outputs
        outputs = self.model(**inputs, output_hidden_states=True)
        logits = outputs.logits
        hidden_states = outputs.hidden_states[-1]
        
        # Compute policy gradient loss
        response_tokens = self.tokenizer(response, return_tensors="pt")["input_ids"].to(self.device)
        response_mask = torch.zeros_like(inputs["input_ids"])
        response_mask[:, -len(response_tokens[0]):] = 1
        
        policy_loss = -torch.mean(torch.log_softmax(logits, dim=-1) * response_mask.unsqueeze(-1)) * reward
        
        # Update model
        policy_loss.backward()
        self.optimizer.step()
        self.optimizer.zero_grad()
    
    def save_model(self, path: str):
        """Save the fine-tuned model and reward model."""
        self.model.save_pretrained(path + "/language_model")
        torch.save(self.reward_model.state_dict(), path + "/reward_model.pth")
    
    def load_model(self, path: str):
        """Load the fine-tuned model and reward model."""
        self.model = AutoModelForCausalLM.from_pretrained(path + "/language_model").to(self.device)
        self.reward_model.load_state_dict(torch.load(path + "/reward_model.pth"))

# Create global RL model instance
rl_model = RLModel()

async def update_model_from_feedback(message: str, response: str, feedback: int):
    """Update the model based on user feedback."""
    # Convert feedback to reward (-1 -> 0, 1 -> 1)
    reward = (feedback + 1) / 2
    
    # Get response embedding
    inputs = rl_model.tokenizer(response, return_tensors="pt").to(rl_model.device)
    with torch.no_grad():
        outputs = rl_model.model(**inputs, output_hidden_states=True)
        response_embedding = outputs.hidden_states[-1].mean(dim=1)
    
    # Compute reward and update policy
    reward = rl_model.compute_reward(response_embedding, reward)
    rl_model.update_policy(message, response, reward)