class User:
    
    def __init__(self,id,temperature,top_p,frequency_penalty,presence_penalty): 
        self.id= id
        self.temperature = temperature
        self.top_p = top_p
        self.frequency_penalty = frequency_penalty
        self.presence_penalty = presence_penalty
    
    def get_id(self):
        return self.id
    
    def get_temperature(self):
        return self.temperature
    
    def get_top_p(self):
        return self.top_p
    
    def get_frequency_penalty(self):
        return self.frequency_penalty
    
    def get_presence_penalty(self):
        return self.presence_penalty
