#!/usr/bin/env python
#
# tournament.py -- implementation of a Swiss-system tournament
#

import psycopg2
import random


def connect():
    """Connect to the PostgreSQL database.  Returns a database connection."""
    return psycopg2.connect("dbname=tournament")


def deleteMatches():
    """Remove all the match records from the database."""
    db = connect()
    cur = db.cursor()
    cur.execute("delete from matches where id > 0;")
    db.commit()
    db.close()


def deletePlayers():
    """Remove all the player records from the database."""
    db = connect()
    cur = db.cursor()
    cur.execute("delete from players where id > 0;")
    db.commit()
    db.close()


def countPlayers():
    """Returns the number of players currently registered."""
    db = connect()
    cur = db.cursor()
    cur.execute("select count(id) from players;")
    rows = cur.fetchall()
    db.close()
    return rows[0][0] if rows else 0


def registerPlayer(name):
    """Adds a player to the tournament database.

    The database assigns a unique serial id number for the player.  (This
    should be handled by your SQL database schema, not in your Python code.)

    Args:
      name: the player's full name (need not be unique).
    """
    if name is None:
        name = ""
    db = connect()
    cur = db.cursor()
    cur.execute("""
insert into players values
( default, %s, default );""", (name, ))
    db.commit()
    db.close()


def playerStandings():
    """Returns a list of the players and their win records, sorted by wins.

    The first entry in the list should be the player in first place, or a
    player tied for first place if there is currently a tie.

    Returns:
      A list of tuples, each of which contains (id, name, wins, matches):
        id: the player's unique id (assigned by the database)
        name: the player's full name (as registered)
        wins: the number of matches the player has won
        matches: the number of matches the player has played
    """
    standings = []
    db = connect()
    cur = db.cursor()
    cur.execute("""
select
    p.id,
    p.name,
    count(m.winner) as winner_count
from players p
left join matches m on p.id=m.winner
group by p.id
order by winner_count desc;""")
    rows = cur.fetchall()

    for row in rows:
        cur.execute("select count(id) from matches where winner=%s;",
                    (row[0], ))
        winsRow = cur.fetchall()
        matches = winsRow[0][0] if winsRow else 0

        # Players assigned a bye are registered as both the winner and loser,
        # so we have to only count winner player IDs on bye matches
        # to avoid double-counting those matches.
        cur.execute("""
select count(id)
from matches
where loser=%s and winner<>%s;""", (row[0], row[0]))
        losesRow = cur.fetchall()
        matches += losesRow[0][0] if losesRow else 0

        standings.append([row[0], row[1], row[2], matches])

    db.close()
    return standings


def reportMatch(winner, loser):
    """Records the outcome of a single match between two players.

    Args:
      winner:  the id number of the player who won
      loser:  the id number of the player who lost
    Returns:
      True on success, False on failure
    """

    if winner is None or loser is None:
        return False

    db = connect()
    cur = db.cursor()
    cur.execute("insert into matches values (default, %s, %s, default);",
                (winner, loser))
    db.commit()
    db.close()
    return True


def swissPairings():
    """Returns a list of pairs of players for the next round of a match.

    Assuming that there are an even number of players registered, each player
    appears exactly once in the pairings.  Each player is paired with another
    player with an equal or nearly-equal win record, that is, a player adjacent
    to him or her in the standings.

    If a player is matched with himself, the player has received a bye win.

    Returns:
      A list of tuples, each of which contains (id1, name1, id2, name2)
        id1: the first player's unique id
        name1: the first player's name
        id2: the second player's unique id
        name2: the second player's name
    """
    pairings = []
    standings = playerStandings()
    if standings is None or len(standings) == 0:
        return None
    db = connect()
    cur = db.cursor()
    byeIndex = None
    byeStanding = None
    if len(standings) % 2 != 0:
        byeIndex = random.randrange(len(standings))
        byeStanding = standings[byeIndex]
        del standings[byeIndex]

    sindex = 0
    while sindex + 1 < len(standings):
        p1Id = standings[sindex][0]
        cur.execute("select name from players where id=%s;",
                    (p1Id, ))
        p1Row = cur.fetchall()
        p1Name = p1Row[0][0] if p1Row else ""
        p2Id = standings[sindex + 1][0]
        cur.execute("select name from players where id=%s;",
                    (p2Id, ))
        p2Row = cur.fetchall()
        p2Name = p2Row[0][0] if p2Row else ""
        pairings.append([p1Id, p1Name, p2Id, p2Name])
        sindex += 2

    if byeIndex is not None:
        byeId = byeStanding[0]
        cur.execute("select name from players where id=%s",
                    (byeId, ))
        byeRow = cur.fetchall()
        byeName = byeRow[0][0] if byeRow else ""
        pairings.append([byeId, byeName, byeId, byeName])
    db.close()
    return pairings

