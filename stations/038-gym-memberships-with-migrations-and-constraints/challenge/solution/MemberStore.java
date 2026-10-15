package com.fitnest.members;

import com.fasterxml.jackson.annotation.JsonInclude;
import org.springframework.jdbc.core.simple.JdbcClient;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.Optional;

/** Members, plans and memberships with JdbcClient: plain SQL, named parameters, rows mapped to records. */
@Repository
class MemberStore {

    @JsonInclude(JsonInclude.Include.NON_NULL)
    record Member(long id, String name, String phone, String email) {
    }

    record Plan(String code, String name, int months, long pricePaise) {
    }

    record Membership(long id, long memberId, String planCode, LocalDate startsOn, LocalDate endsOn, long pricePaise, int frozenDays) {
    }

    private final JdbcClient jdbc;

    MemberStore(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    Member addMember(String name, String phone, String email) {
        return jdbc.sql("INSERT INTO members (name, phone, email) VALUES (:name, :phone, :email) RETURNING id, name, phone, email")
                .param("name", name).param("phone", phone).param("email", email)
                .query(Member.class).single();
    }

    Optional<Member> member(long id) {
        return jdbc.sql("SELECT id, name, phone, email FROM members WHERE id = :id").param("id", id).query(Member.class).optional();
    }

    Optional<Plan> plan(String code) {
        return jdbc.sql("SELECT code, name, months, price_paise FROM plans WHERE code = :code").param("code", code).query(Plan.class).optional();
    }

    Membership addMembership(long memberId, Plan plan, LocalDate startsOn, LocalDate endsOn) {
        return jdbc.sql("""
                        INSERT INTO memberships (member_id, plan_code, starts_on, ends_on, price_paise)
                        VALUES (:member, :plan, :starts, :ends, :price)
                        RETURNING id, member_id, plan_code, starts_on, ends_on, price_paise, frozen_days""")
                .param("member", memberId).param("plan", plan.code()).param("starts", startsOn).param("ends", endsOn).param("price", plan.pricePaise())
                .query(Membership.class).single();
    }

    Optional<Membership> membership(long id) {
        return jdbc.sql("SELECT id, member_id, plan_code, starts_on, ends_on, price_paise, frozen_days FROM memberships WHERE id = :id")
                .param("id", id).query(Membership.class).optional();
    }

    Membership freeze(long id, int days) {
        return jdbc.sql("""
                        UPDATE memberships SET ends_on = ends_on + :days, frozen_days = frozen_days + :days WHERE id = :id
                        RETURNING id, member_id, plan_code, starts_on, ends_on, price_paise, frozen_days""")
                .param("days", days).param("id", id).query(Membership.class).single();
    }
}
