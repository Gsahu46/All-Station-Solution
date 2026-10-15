package com.mediqo.doctors;

import org.springframework.data.jpa.repository.JpaRepository;

interface ClinicRepository extends JpaRepository<Clinic, Long> {
}
