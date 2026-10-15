package com.fitnest.members;

import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Optional;

/** Members, plans and memberships with JdbcClient: plain SQL, named parameters, rows mapped to records. */
@Repository
class MemberStore {

    record Member(long id, String name, String phone) {
    }

    record Plan(String code, String name, int months, long pricePaise) {
    }

    record Membership(long id, long memberId, String planCode, LocalDate startsOn, LocalDate endsOn, long pricePaise) {
    }

    private final JdbcClient jdbc;

    MemberStore(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Member addMember(String name, String phone) {
        return jdbc.sql("INSERT INTO members (name, phone) VALUES (:name, :phone) RETURNING id, name, phone")
                .param("name", name).param("phone", phone)
                .query(Member.class).single();
    }

    Optional<Member> member(long id) {
        return jdbc.sql("SELECT id, name, phone FROM members WHERE id = :id").param("id", id).query(Member.class).optional();
    }

    Optional<Plan> plan(String code) {
        return jdbc.sql("SELECT code, name, months, price_paise FROM plans WHERE code = :code").param("code", code).query(Plan.class).optional();
    }

    Membership addMembership(long memberId, Plan plan, LocalDate startsOn, LocalDate endsOn) {
        return jdbc.sql("""
                        INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise)
                        VALUES (:member, :plan, :starts, :ends, :price)
                        RETURNING id, member_id, plan_code, starts_on, ends_on, price_paise""")
                .param("member", memberId).param("plan", plan.code()).param("starts", startsOn).param("ends", endsOn).param("price", plan.pricePaise())
                .query(Membership.class).single();
    }
}
