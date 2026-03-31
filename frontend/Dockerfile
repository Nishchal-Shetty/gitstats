FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Copy template config
COPY public/config.js /usr/share/nginx/html/config.js

# Startup script to replace placeholder
COPY docker-entrypoint.sh /docker-entrypoint.d/99-config.sh

RUN chmod +x /docker-entrypoint.d/99-config.sh

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]