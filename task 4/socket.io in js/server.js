const path = require("path");
const Fastify = require("fastify");
const fastifyStatic = require("@fastify/static");
const { Server } = require("socket.io");

const fastify = Fastify({ logger: true });

// Serve static files (index.html) from same folder
fastify.register(fastifyStatic, {
  root: __dirname,
  prefix: "/",
});

// Home route
fastify.get("/", async (req, reply) => {
  return reply.sendFile("index.html");
});

async function start() {
  await fastify.listen({ port: 3000, host: "0.0.0.0" });

  // Attach Socket.IO to Fastify's underlying server
  const io = new Server(fastify.server, {
    cors: { origin: "*" },
  });

  io.on("connection", (socket) => {
    console.log("🟢 user connected");

    socket.on("chat", (msg) => {
      console.log("💬 message:", msg);
      io.emit("chat", msg);
    });

    socket.on("disconnect", () => {
      console.log("🔴 user disconnected");
    });
  });

  console.log("Server running at http://localhost:3000");
}

start().catch((err) => {
  fastify.log.error(err);
  process.exit(1);
});
