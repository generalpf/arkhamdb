CREATE TABLE session(
    _id integer PRIMARY KEY AUTOINCREMENT,
    sessionid char(36) NOT NULL UNIQUE,
    sourceip varchar(15) NULL,
    title text NOT NULL,
    created datetime NOT NULL
);

CREATE TABLE session_neighbourhoodcard(
    neighbourhoodcardid integer,
    sessionid integer,
    discarded tinyint DEFAULT 0,
    pinned tinyint DEFAULT 0,
    FOREIGN KEY(neighbourhoodcardid) REFERENCES neighbourhoodcard(_id),
    FOREIGN KEY(sessionid) REFERENCES session(_id)
);

ALTER TABLE neighbourhoodcard DROP COLUMN discarded;

CREATE TABLE session_otherworldcard(
    otherworldcardid integer,
    sessionid integer,
    discarded tinyint DEFAULT 0,
    pinned tinyint DEFAULT 0,
    FOREIGN KEY(otherworldcardid) REFERENCES otherworldcard(_id),
    FOREIGN KEY(sessionid) REFERENCES session(_id)
);

ALTER TABLE otherworldcard DROP COLUMN discarded;

CREATE TABLE session_cultencountercard(
    cultencountercardid integer,
    sessionid integer,
    discarded tinyint default 0,
    FOREIGN KEY(cultencountercardid) REFERENCES cultencountercard(_id),
    FOREIGN KEY(sessionid) REFERENCES session(_id)
);

ALTER TABLE cultencountercard DROP COLUMN discarded;

CREATE TABLE session_exhibitencountercard(
    exhibitencountercardid integer,
    sessionid integer,
    discarded tinyint default 0,
    FOREIGN KEY(exhibitencountercardid) REFERENCES exhibitencountercard(_id),
    FOREIGN KEY(sessionid) REFERENCES session(_id)
);

ALTER TABLE exhibitencountercard DROP COLUMN discarded;

CREATE TABLE session_reckoningcard(
    reckoningcardid integer,
    sessionid integer,
    discarded tinyint default 0,
    FOREIGN KEY(reckoningcardid) REFERENCES reckoningcard(_id),
    FOREIGN KEY(sessionid) REFERENCES session(_id)
);

ALTER TABLE reckoningcard DROP COLUMN discarded;
