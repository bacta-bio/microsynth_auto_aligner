# Microsynth Auto Aligner

Automated sequencing data processing tool for Bacta. Programmatically processes Microsynth sequencing data and generates alignments that are automatically uploaded to Benchling, where they are associated with reference sequences.

## Why This Tool?

- 🚀 Saves time by eliminating manual alignment work in SnapGene, Geneious, or Benchling
- 🌐 Enables everyone to generate and view alignments without specialized molecular biology software
- 📦 Centralizes and stores all sequencing data in LIMS for easy reference
- 🤖 Automated workflow: download → process → upload to Benchling

## Quick Start

### 1. Build the Docker Image
```bash
docker build -t microsynth-aligner .
```

### 2. Set Up Environment Variables
Create a `.env` file with your Benchling credentials:
```bash
BENCHLING_DOMAIN=your-domain.benchling.com
BENCHLING_API_KEY=your_api_key_here
```

### 3. Add Your Bacta Logo (Optional)
Place your logo at `static/images/bacta-logo.png`:
- Recommended size: 300x80 pixels
- Format: PNG with transparency
- See [Bacta](https://bacta.bio/) for brand guidelines

### 4. Run the Container
```bash
# Local development
docker run --rm -it -p 8080:8080 --env-file .env microsynth-aligner

# Production deployment
docker run -d \
  --name microsynth-aligner \
  -p 8080:8080 \
  --env-file .env \
  --restart unless-stopped \
  microsynth-aligner
```

### 5. Access the Web Interface
Open your browser at: `http://localhost:8080` or `http://your-server-ip:8080`

## Usage

1. **Upload Files**: Click "Choose Files" and select your Microsynth FASTA files (`.fasta`, `.fa`, `.gbk`, `.genbank`) or upload a zip archive
2. **Run Alignment**: Click "Upload & Run Alignment"
3. **Monitor Progress**: Watch real-time logs in the progress section
4. **Results**: Alignments are automatically uploaded to Benchling

### Supported File Formats
- `.fasta`, `.fa` - FASTA sequence files
- `.gbk`, `.genbank` - GenBank format files
- `.zip` - Archive containing multiple files (auto-extracted)

**Note:** The microsynth sample name (e.g., TUBEXXXX) should match your Benchling container identifiers for automatic matching.

## Features

- 📤 **File Upload**: Direct browser upload - no volume mounting required
- 📊 **Real-time Progress**: Live logging of the alignment process
- 🔄 **Auto Cleanup**: Temporary files automatically removed after processing
- ✅ **Auto Upload**: Results automatically sent to Benchling via API
- 🎨 **Modern UI**: Clean, responsive design with Bacta branding
- 📦 **Multiple Files**: Upload multiple files or a zip archive at once
- 🔒 **Secure**: Files are temporarily stored and automatically cleaned up

## Production Deployment

### Docker Compose (Recommended)

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  microsynth-aligner:
    image: microsynth-aligner
    container_name: microsynth-aligner
    ports:
      - "8080:8080"
    env_file:
      - .env
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

### Nginx Reverse Proxy Setup

For SSL and domain routing, add to your nginx configuration:

```nginx
server {
    listen 80;
    server_name microsynth.yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### Logs Not Appearing
- Check browser console for JavaScript errors
- Verify server is running: `docker logs microsynth-aligner`

### Upload Issues
- Maximum upload size: 100MB
- Ensure files are in supported formats
- Check your network connection stability

### Benchling API Errors
- Verify `.env` file has correct credentials
- Check API key permissions in Benchling
- Ensure BENCHLING_DOMAIN is correct

### Container Issues
- Check container status: `docker ps -a`
- View logs: `docker logs -f microsynth-aligner`
- Restart container: `docker restart microsynth-aligner`

## Maintenance

### Update the Application
```bash
docker build -t microsynth-aligner .
docker stop microsynth-aligner
docker rm microsynth-aligner
# Run with the new image (see "Run the Container" above)
```

### View Logs
```bash
docker logs -f microsynth-aligner
```

### Backup Environment File
Keep your `.env` file backed up and secure - it contains sensitive API credentials.

## Technical Details

- **Max Upload Size**: 100MB per request
- **Temporary Storage**: `/tmp/uploads` (auto-cleaned after processing)
- **Port**: 8080
- **Technology**: Python Flask web server with custom frontend
- **Dependencies**: Benchling SDK, Biopython, Pandas

---

**Bacta** - AI-powered bioproduction for industrial ingredients  
Website: [https://bacta.bio/](https://bacta.bio/)
