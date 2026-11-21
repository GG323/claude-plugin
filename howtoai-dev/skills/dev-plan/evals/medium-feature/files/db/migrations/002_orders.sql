create table orders (id serial primary key, user_id int not null references users(id), total numeric(10,2) not null, day date not null);
