FROM nginx:alpine

# Install sed (should already be available in alpine)
# Copy static files
COPY static/ /usr/share/nginx/html/

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose port
EXPOSE 80

# Use entrypoint to inject environment variables
ENTRYPOINT ["/entrypoint.sh"]

