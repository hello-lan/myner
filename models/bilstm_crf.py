import torch as t
import torch.nn as nn
from torchcrf import CRF

from .basic_module import BasicModule


class SpatialDropout(nn.Dropout2d):
    def __init__(self, p=0.6):
        super(SpatialDropout, self).__init__(p=p)

    def forward(self, x):
        x = x.unsqueeze(2)  # (N, T, 1, K)
        x = x.permute(0, 3, 2, 1)  # (N, K, 1, T)
        x = super(SpatialDropout, self).forward(x)  # (N, K, 1, T), some features are masked
        x = x.permute(0, 3, 2, 1)  # (N, T, 1, K)
        x = x.squeeze(2)  # (N, T, K)
        return x


class BiLSTM_CRF(BasicModule):
    def __init__(self,vocab_size,embedding_size,hidden_size,
                 label_size,drop_p = 0.1):
        super(BiLSTM_CRF, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_size)
        self.bilstm = nn.LSTM(input_size=embedding_size,
                              hidden_size=hidden_size,
                              batch_first=True,
                              num_layers=2,
                              dropout=drop_p,
                              bidirectional=True)
        self.dropout = SpatialDropout(drop_p)
        self.layer_norm = nn.LayerNorm(hidden_size * 2)
        self.classifier = nn.Linear(hidden_size * 2, label_size)
        self.crf = CRF(label_size,batch_first=True)

    def forward(self, inputs_ids, input_mask):
        embs = self.embedding(inputs_ids)
        embs = self.dropout(embs)    # output: batch * seq * vocab
        embs = embs * input_mask.float().unsqueeze(2)
        seqence_output, _ = self.bilstm(embs)    #　output size： batch * seq * (hidden * 2)
        seqence_output= self.layer_norm(seqence_output)
        emissions = self.classifier(seqence_output)
        return emissions

    def forward_loss(self, input_ids, input_mask, input_tags):
        emissions = self.forward(input_ids, input_mask)
        loss = -1 * self.crf(emissions, input_tags, mask=input_mask,reduction='mean')
        return loss
        
    def forward_tags(self, input_ids, input_mask):
         emissions = self.forward(input_ids, input_mask)
         tags = self.crf.decode(emissions, input_mask)
         return tags
