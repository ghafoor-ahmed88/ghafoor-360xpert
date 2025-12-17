const fastify = require('fastify')({ logger: true });
const path = require('path');
const bcrypt = require('bcryptjs'); 
const sequelize = require('./db');
const User = require("./models/user.model");


// =======================
// Plugins
// =======================
const fastifyCors = require('@fastify/cors');
fastify.register(fastifyCors, { origin: "*" });

const fastifyStatic = require('@fastify/static');
fastify.register(fastifyStatic, {
  root: path.join(__dirname, 'public'),
  prefix: '/',
});

// =======================
// DB Sync
// =======================
sequelize.sync().then(() => console.log('DB connected'));

// =======================
// Routes
// =======================

// Serve index.html
fastify.get('/', async (req, reply) => {
  return reply.sendFile('index.html');
});

// POST /register
fastify.post('/register', async (req, reply) => {
  console.log(req.body);
  const { name, email, password } = req.body;
  const hashedPassword = await bcrypt.hash(password, 10); 
  const user = await User.create({ name, email, password: hashedPassword });
  return user;
});

// POST /login
fastify.post('/login', async (req, reply) => {
  const { email, password } = req.body;
  const user = await User.findOne({ where: { email } });
  if (!user) return reply.code(401).send({ message: 'Invalid credentials' });

  const valid = await bcrypt.compare(password, user.password); // ✅ bcryptjs compare
  if (!valid) return reply.code(401).send({ message: 'Invalid credentials' });

  return { message: 'Login successful', user: { id: user.id, name: user.name, email: user.email } };
});

// GET /users
fastify.get('/users', async () => {
  return await User.findAll({ attributes: ['id', 'name', 'email'] });
});

// GET /users/:id
fastify.get('/users/:id', async (req, reply) => {
  const user = await User.findByPk(req.params.id, { attributes: ['id', 'name', 'email'] });
  if (!user) return reply.code(404).send({ message: 'User not found' });
  return user;
});

// PUT /users/:id
fastify.put('/users/:id', async (req, reply) => {
  const user = await User.findByPk(req.params.id);
  if (!user) return reply.code(404).send({ message: 'User not found' });
  if (req.body.password) {
    req.body.password = await bcrypt.hash(req.body.password, 10); // ✅ hash if password updated
  }

  await user.update(req.body);
  return user;
});

// PATCH /users/:id
fastify.patch('/users/:id', async (req, reply) => {
  const user = await User.findByPk(req.params.id);
  if (!user) return reply.code(404).send({ message: 'User not found' });

  if (req.body.password) {
    req.body.password = await bcrypt.hash(req.body.password, 10); // ✅ hash if password updated
  }

  await user.update(req.body);
  return user;
});

// DELETE /users/:id
fastify.delete('/users/:id', async (req, reply) => {
  const user = await User.findByPk(req.params.id);
  if (!user) return reply.code(404).send({ message: 'User not found' });
  await user.destroy();
  return { message: 'User deleted' };
});

// =======================
// Start Server
// =======================
const start = async () => {
  try {
    await fastify.listen({ port: 3000 });
    console.log('Server running on http://localhost:3000');
  } catch (err) {
    fastify.log.error(err);
    process.exit(1);
  }
};

start();