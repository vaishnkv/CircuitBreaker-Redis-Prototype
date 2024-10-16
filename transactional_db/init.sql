\c transact_db;

-- Create the User table
CREATE TABLE User_table (
    user_id SERIAL PRIMARY KEY,
    user_name VARCHAR(255) NOT NULL
);

-- Create the Post table
CREATE TABLE Post_table (
    post_id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES User_table(user_id) ON DELETE CASCADE
);

-- Create the Impression table
CREATE TABLE Impression_table (
    impression_id SERIAL PRIMARY KEY,
    impression_type VARCHAR(4) CHECK (impression_type IN ('UP', 'DOWN')),
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    time_of_impression TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_post FOREIGN KEY(post_id) REFERENCES Post_table(post_id) ON DELETE CASCADE,
    CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES User_table(user_id) ON DELETE CASCADE
);

-- Create the Score table
CREATE TABLE Score_table (
    post_id INT PRIMARY KEY,
    score INT NOT NULL DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_post FOREIGN KEY(post_id) REFERENCES Post_table(post_id) ON DELETE CASCADE
);

