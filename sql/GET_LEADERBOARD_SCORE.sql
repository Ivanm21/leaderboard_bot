SELECT 
users.name, 
COALESCE(SUM(a.points), 0) as 'points'
 FROM `leaderboard`.`leaderboards` lb
 JOIN `leaderboard`.`participants` p 
    ON lb.id = p.leaderboard_id
 JOIN `leaderboard`.`users` users
    ON p.user_id = users.id
 LEFT JOIN `leaderboard`.`performed_activity` pa
    ON p.id = pa.participant_id
 LEFT JOIN `leaderboard`.`activities` a
     ON pa.activity_id = a.id 
WHERE lb.id = -443487068
GROUP BY p.id
ORDER BY COALESCE(SUM(a.points), 0) DESC
