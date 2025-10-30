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
Create a `.env` file with your Benchling OAuth2 credentials:
```bash
BENCHLING_CLIENT_ID=your_client_id_here
BENCHLING_CLIENT_SECRET=your_client_secret_here
BENCHLING_BASE_URL=https://api.benchling.com/v2
BENCHLING_TOKEN_URL=https://api.benchling.com/v2/token
REQUEST_TIMEOUT=30
MAX_RETRIES=3
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

### Docker Compose with Nginx proxy

Run an Nginx container that proxies to the Gunicorn app over the Docker network.

docker-compose.yml (provided in repo):

Nginx base config (nginx/nginx.conf) and virtual host (nginx/conf.d/app.conf) are included. Update `server_name`, TLS cert paths, and `client_max_body_size` as needed.

## 🐳 Docker Deployment

```bash
# Build the Docker image (Dockerfile now lives in ./docker)
docker build -f docker/Dockerfile -t microsynth-aligner .

# Run with environment file
docker run -d --env-file .env microsynth-aligner
```

### Deploying to Docker Hub (multi-arch)

On the local machine:

```bash
export DOCKER_USER="mnbactabio"
export IMAGE="bacta-apps"
export VERSION="1.0.0"

# From the repository root (where the docker/ directory lives)

# Create/use a multi-arch builder (first time only)
docker buildx create --name multi-arch-builder --use 2>/dev/null || docker buildx use multi-arch-builder

docker buildx build -f docker/Dockerfile \
  --platform linux/amd64,linux/arm64 \
  -t $DOCKER_USER/$IMAGE:$VERSION \
  -t $DOCKER_USER/$IMAGE:latest \
  --push .
```

On the instance:

```bash
# 1) Set vars (match what you pushed)
export DOCKER_USER="mnbactabio"
export IMAGE="bacta-apps"
export VERSION="1.0.0"

# 2) Login (use token if private)
echo "$DOCKER_TOKEN" | docker login -u "$DOCKER_USER" --password-stdin

# 3) Pull the image
docker pull $DOCKER_USER/$IMAGE:$VERSION

# 4) Run it (adjust ports/env/volumes as needed)
docker run -d --name benchling --env-file .env -p 8080:8080 $DOCKER_USER/$IMAGE:$VERSION

### Orchestrate with docker compose

To run the full Nginx + app stack:

```bash
docker compose -f docker/docker-compose.yml up -d
```

Configs referenced by the compose file are under `docker/nginx/`.
```

Notes:
- If your Dockerfile is not at the repo root, change `-f Dockerfile` to its path (e.g., `-f docker/Dockerfile`).
- Replace `benchling`/`microsynth-aligner` with your preferred image name.
- Expose and map port 8080 if accessing via a browser.

## Troubleshooting

### Logs Not Appearing
- Check browser console for JavaScript errors
- Verify server is running: `docker logs microsynth-aligner`

### Upload Issues
- Maximum upload size: 100MB
- Ensure files are in supported formats
- Check your network connection stability

### Benchling API Errors
- Verify `.env` file has correct OAuth2 credentials
- Check OAuth2 app permissions in Benchling
- Ensure BENCHLING_CLIENT_ID and BENCHLING_CLIENT_SECRET are correct
- Verify BENCHLING_BASE_URL points to the correct API endpoint

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

## Project Structure

```
microsynth_auto_aligner/
├── src/                          # Main application code
│   ├── app.py                    # Flask web server
│   └── microsynth_auto_aligner.py # Core alignment logic
├── benchling/                    # Custom Benchling API client
│   ├── __init__.py
│   ├── auth.py                   # OAuth2 authentication
│   ├── client.py                 # API client wrapper
│   └── config.py                 # Configuration management
├── static/                       # Web assets
├── templates/                     # HTML templates
├── env.example                   # Environment variables template
└── requirements.txt              # Python dependencies
```

## OAuth2 Setup

This application uses OAuth2 Client Credentials flow for Benchling API authentication. To set up:

1. **Create a Benchling App**: In your Benchling instance, go to Settings → Apps & Integrations → Create App
2. **Configure OAuth2**: Enable OAuth2 Client Credentials and note your Client ID and Secret
3. **Set Permissions**: Ensure the app has necessary permissions for:
   - Reading containers and their contents
   - Creating nucleotide alignments
   - Accessing entity schemas

## Technical Details

- **Max Upload Size**: 100MB per request
- **Temporary Storage**: `/tmp/uploads` (auto-cleaned after processing)
- **Port**: 8080
- **Technology**: Python Flask web server with custom frontend
- **Dependencies**: Custom Benchling API client, Biopython, Pandas, python-dotenv
- **Authentication**: OAuth2 Client Credentials flow

---

**Bacta** - AI-powered bioproduction for industrial ingredients  
Website: [https://bacta.bio/](https://bacta.bio/)
