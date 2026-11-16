FROM node:22-bookworm

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

RUN npx playwright install --with-deps chromium

COPY . .

ENV CI=true

CMD ["npx", "playwright", "test"]

