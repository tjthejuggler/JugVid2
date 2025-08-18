import torch
import torch.nn as nn
import torch.nn.functional as F

# -------------------------------------------------
# ConvLSTM Cell
# -------------------------------------------------
class ConvLSTMCell(nn.Module):
    """
    A basic ConvLSTM cell.
    Processes one time step and returns the next hidden and cell states.
    """
    def __init__(self, input_dim, hidden_dim, kernel_size, bias=True):
        super(ConvLSTMCell, self).__init__()
        padding = kernel_size // 2  # keep same spatial dimensions
        self.hidden_dim = hidden_dim
        # The convolution takes concatenated input and previous hidden state
        self.conv = nn.Conv2d(in_channels=input_dim + hidden_dim,
                              out_channels=4 * hidden_dim,
                              kernel_size=kernel_size,
                              padding=padding,
                              bias=bias)

    def forward(self, input_tensor, cur_state):
        h_cur, c_cur = cur_state
        # Concatenate along the channel dimension
        combined = torch.cat([input_tensor, h_cur], dim=1)
        combined_conv = self.conv(combined)
        # Split the convolution output into four parts for input, forget, output, and cell gate
        cc_i, cc_f, cc_o, cc_g = torch.split(combined_conv, self.hidden_dim, dim=1)
        i = torch.sigmoid(cc_i)
        f = torch.sigmoid(cc_f)
        o = torch.sigmoid(cc_o)
        g = torch.tanh(cc_g)
        # Update cell state and hidden state
        c_next = f * c_cur + i * g
        h_next = o * torch.tanh(c_next)
        return h_next, c_next

    def init_hidden(self, batch_size, spatial_size):
        height, width = spatial_size
        device = next(self.parameters()).device
        return (torch.zeros(batch_size, self.hidden_dim, height, width, device=device),
                torch.zeros(batch_size, self.hidden_dim, height, width, device=device))

# -------------------------------------------------
# ConvLSTM Module (multiple layers/time unrolling)
# -------------------------------------------------
class ConvLSTM(nn.Module):
    """
    Processes an input sequence (B, T, C, H, W) using ConvLSTM cells.
    Returns the output sequence and the final hidden states.
    """
    def __init__(self, input_dim, hidden_dim, kernel_size, num_layers, bias=True):
        super(ConvLSTM, self).__init__()
        self.num_layers = num_layers
        cell_list = []
        for i in range(num_layers):
            cur_input_dim = input_dim if i == 0 else hidden_dim
            cell_list.append(ConvLSTMCell(cur_input_dim, hidden_dim, kernel_size, bias))
        self.cell_list = nn.ModuleList(cell_list)

    def forward(self, input_tensor):
        # input_tensor shape: (B, T, C, H, W)
        batch_size, seq_len, _, height, width = input_tensor.size()
        hidden_states = []
        cell_states = []
        # Initialize hidden and cell states for each layer
        for i in range(self.num_layers):
            h, c = self.cell_list[i].init_hidden(batch_size, (height, width))
            hidden_states.append(h)
            cell_states.append(c)
        outputs = []
        # Process each time step sequentially
        for t in range(seq_len):
            x = input_tensor[:, t, :, :, :]
            for i, cell in enumerate(self.cell_list):
                h, c = cell(x, (hidden_states[i], cell_states[i]))
                hidden_states[i] = h
                cell_states[i] = c
                x = h  # input for next layer
            outputs.append(h)
        # Stack outputs along the time dimension: (B, T, hidden_dim, H, W)
        outputs = torch.stack(outputs, dim=1)
        return outputs, (hidden_states, cell_states)

# -------------------------------------------------
# End-to-End Ball Tracking Network
# -------------------------------------------------
class BallTracker(nn.Module):
    """
    This model accepts a sequence of frames and outputs a ball localization heatmap.
    It uses:
      1. A CNN backbone to extract spatial features from each frame.
      2. A ConvLSTM to fuse temporal information.
      3. A final convolution to produce a heatmap.
    """
    def __init__(self, num_frames=5, hidden_dim=64):
        super(BallTracker, self).__init__()
        self.num_frames = num_frames
        
        # CNN backbone: Simple feature extractor
        # Input: 3 channels; Output: 64 channels; Spatial dimensions reduced by factor 4.
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(3, 32, kernel_size=3, padding=1),  # (B, 32, H, W)
            nn.ReLU(),
            nn.MaxPool2d(2),                           # (B, 32, H/2, W/2)
            nn.Conv2d(32, 64, kernel_size=3, padding=1), # (B, 64, H/2, W/2)
            nn.ReLU(),
            nn.MaxPool2d(2)                            # (B, 64, H/4, W/4)
        )
        # Temporal fusion using a one-layer ConvLSTM
        self.convlstm = ConvLSTM(input_dim=64, hidden_dim=hidden_dim, kernel_size=3, num_layers=1)
        # Final convolution to produce a single-channel heatmap
        self.heatmap_conv = nn.Conv2d(hidden_dim, 1, kernel_size=1)

    def forward(self, x):
        """
        x: Input tensor with shape (B, T, 3, H, W)
        Returns:
          heatmap: A heatmap of ball location with shape (B, 1, H, W)
        """
        B, T, C, H, W = x.size()
        # Process each frame through the CNN backbone
        x = x.view(B * T, C, H, W)
        features = self.feature_extractor(x)  # (B*T, 64, H/4, W/4)
        _, C_feat, H_feat, W_feat = features.size()
        features = features.view(B, T, C_feat, H_feat, W_feat)
        
        # Fuse temporal information with ConvLSTM
        lstm_out, _ = self.convlstm(features)  # (B, T, hidden_dim, H_feat, W_feat)
        # Use the last time step's output for the final prediction
        last_out = lstm_out[:, -1, :, :, :]  # (B, hidden_dim, H_feat, W_feat)
        heatmap = self.heatmap_conv(last_out)  # (B, 1, H_feat, W_feat)
        # Upsample heatmap to original image resolution
        heatmap = F.interpolate(heatmap, scale_factor=4, mode='bilinear', align_corners=False)
        return heatmap

# -------------------------------------------------
# Example usage (dummy data)
# -------------------------------------------------
if __name__ == '__main__':
    # Create an instance of the BallTracker model.
    model = BallTracker(num_frames=5, hidden_dim=64)
    # Print the model summary
    print(model)
    
    # Dummy input: Batch size 2, 5 consecutive frames, 3 channels, 256x256 resolution
    dummy_input = torch.randn(2, 5, 3, 256, 256)
    # Forward pass: Output heatmap with shape (B, 1, H, W)
    output_heatmap = model(dummy_input)
    print("Output heatmap shape:", output_heatmap.shape)
