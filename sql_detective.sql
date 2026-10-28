-- SQL Detective Challenge (PostgreSQL)
-- Load the data first:  psql hiring_ops -f sql/detective_data.sql
-- Then run:             psql hiring_ops -f sql_detective.sql


-- Q1: All currently open job postings with the owning recruiter's name.
-- LEFT JOIN so an open posting with a missing/unknown recruiter would still be listed.
SELECT jp.id, jp.title, jp.department, jp.opened_date, r.name AS recruiter_name
FROM job_postings jp
LEFT JOIN recruiters r ON r.id = jp.recruiter_id
WHERE jp.status = 'open'
ORDER BY jp.id;


-- Q2: For each job posting, how many applicants reached the Final interview stage.
-- The stage filter sits in the JOIN condition (not WHERE) so postings with no Final
-- interviews still appear with 0. COUNT(DISTINCT) avoids double-counting an applicant
-- who had more than one Final for the same posting.
SELECT jp.id, jp.title, jp.status,
       COUNT(DISTINCT i.applicant_id) AS applicants_reached_final
FROM job_postings jp
LEFT JOIN interviews i
       ON i.job_posting_id = jp.id
      AND i.stage = 'Final'
GROUP BY jp.id, jp.title, jp.status
ORDER BY jp.id;


-- Q3: Every person who effectively applied to more than one job posting.
-- Assumptions:
--  * The schema has no applications table, so an application is inferred from
--    interview records (applicant + posting).
--  * "Effectively": the same person can appear as several applicant rows. Ananya Rao
--    is ids 1 and 2 with emails differing only in case, so a person is identified by
--    LOWER(TRIM(email)).
--  * Rows without a usable email are excluded: NULL/blank addresses cannot reliably
--    identify a person and must not be grouped together as one applicant.
--  * Count DISTINCT postings: several interview rounds for one posting are one
--    application. Group by posting id, never by title (postings 1, 2 and 7 share
--    the title 'Backend Engineer I' but are different postings).
SELECT LOWER(TRIM(a.email))                                   AS person_email,
       MIN(a.full_name)                                       AS full_name,
       ARRAY_AGG(DISTINCT a.id ORDER BY a.id)                 AS applicant_ids,
       COUNT(DISTINCT i.job_posting_id)                       AS postings_applied,
       ARRAY_AGG(DISTINCT i.job_posting_id ORDER BY i.job_posting_id) AS posting_ids
FROM applicants a
JOIN interviews i ON i.applicant_id = a.id
WHERE NULLIF(LOWER(TRIM(a.email)), '') IS NOT NULL
GROUP BY LOWER(TRIM(a.email))
HAVING COUNT(DISTINCT i.job_posting_id) > 1
ORDER BY full_name;


-- Q4: Final-stage conversion rate per recruiter (passed / total Final interviews),
-- only recruiters with at least 3 Final-stage interviews.
-- Denominator: all Final interviews, including failed, no_show and pending (NULL).
-- Numeric cast avoids integer division.
SELECT r.id, r.name,
       COUNT(*)                                          AS final_interviews,
       COUNT(*) FILTER (WHERE i.outcome = 'passed')      AS final_passed,
       ROUND(100.0 * COUNT(*) FILTER (WHERE i.outcome = 'passed') / COUNT(*), 2)
                                                         AS conversion_rate_pct
FROM recruiters r
JOIN job_postings jp ON jp.recruiter_id = r.id
JOIN interviews i    ON i.job_posting_id = jp.id AND i.stage = 'Final'
GROUP BY r.id, r.name
HAVING COUNT(*) >= 3
ORDER BY conversion_rate_pct DESC, r.id;


-- Q5 (Bonus): The recruiter with the most successful placements (passed at Final)
-- in each department, using a window function.
-- RANK() (not ROW_NUMBER) so a tie at the top returns every tied recruiter.
-- Departments with no passed Finals (Infrastructure here) have no placements to rank
-- and are omitted.
WITH placements AS (
    SELECT jp.department, r.id AS recruiter_id, r.name AS recruiter_name,
           COUNT(*) AS placements
    FROM interviews i
    JOIN job_postings jp ON jp.id = i.job_posting_id
    JOIN recruiters r    ON r.id = jp.recruiter_id
    WHERE i.stage = 'Final' AND i.outcome = 'passed'
    GROUP BY jp.department, r.id, r.name
),
ranked AS (
    SELECT p.*,
           RANK() OVER (PARTITION BY department ORDER BY placements DESC) AS dept_rank
    FROM placements p
)
SELECT department, recruiter_name, placements
FROM ranked
WHERE dept_rank = 1
ORDER BY department, recruiter_name;
