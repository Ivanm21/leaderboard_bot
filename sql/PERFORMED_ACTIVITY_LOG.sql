SET @leaderboard_id = -443487068;
SET @records = 2;
 
SELECT  
u.name, a.activity_name, a.points, pa.time_created
FROM `leaderboard`.`performed_activity` pa
JOIN `leaderboard`.`activities` a
    ON a.id = pa.activity_id
JOIN `leaderboard`.`participants` p
    ON p.id = pa.participant_id
JOIN `leaderboard`.`users` u
    ON u.id = p.user_id
WHERE a.leaderboard_id = @leaderboard_id
ORDER BY pa.time_created DESC
LIMIT 10 