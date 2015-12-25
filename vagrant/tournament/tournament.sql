-- Table definitions for the tournament project.
--
-- Put your SQL 'create table' statements in this file; also 'create view'
-- statements if you choose to use it.
--
-- You can write comments in this file by starting them with two dashes, like
-- these lines here.

create table players
    (
    id serial primary key not null,
    name text not null,
    created timestamp default clock_timestamp()
    );

create table matches
    (
    id serial primary key not null,
    winner integer references players on delete restrict,
    loser integer references players on delete restrict,
    created timestamp default clock_timestamp()
    );

