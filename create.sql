/* Schema for MyDB Admin DataBase
   Maintain state, backup information for MyDB instances
 */

/* containers
   <data> contains Docker inspect plus the <Info> data
   <c_id> from other tables referances <id>; This is the master table for
   container data. <container> is an archive of all docker instances.
   Data is never removed from this table.
 */
create table containers(
    id SERIAL primary key,
    name Text,
    data JSONB,
    ts TIMESTAMP DEFAULT current_timestamp
);

/* container_state
   maintain current state of MyDB. This table only lists instances
   that should be insalled and running. This data can be use for 
   listing current state and also be used for recover.  Backups are
   based on instances from this table.
 */ 
create table container_state(
    id Integer primary key not null,
    c_id Integer,
    name Text,
    state Text,
    last_state Text,
    observerd Text,
    changed_by Text,
    ts TIMESTAMP DEFAULT current_timestamp
);

/* action_log
   mydb events are logged, create, delete, etc
*/
create table action_log(
    id Integer primary key not null,
    c_id Integer,
    name Text,
    action Text,
    description Text,
    ts TIMESTAMP
);


/*  backups
    backup logs; every backup is logged to this table
 */
create table backups(
    id SERIAL,
    c_id integer,
    name Text,
    state Text,
    backup_id text,
    backup_type text,
    url text,
    command text,
    err_msg text, 
    ts TIMESTAMP DEFAULT current_timestamp
);

CREATE ROLE pgdba with SUPERUSER LOGIN PASSWORD 'fhpsqladmin';
