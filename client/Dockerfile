
# Use Node.js 18 on Alpine for a lightweight build
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files first for caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY . .

# Expose standard Vite port
EXPOSE 5173

# Start the dev server
# --host is needed to expose the server outside the container
CMD ["npm", "run", "dev", "--", "--host"]
